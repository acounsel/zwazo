import csv
import io
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import View, DetailView, ListView
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView

from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Gather, Dial, VoiceResponse, Say

from .forms import SurveyForm, PromptFormSet
from .models import Language, Country, Project, Contact, Prompt
from .models import Survey, Question, QuestionResponse
from .decorators import validate_twilio_request

logger = logging.getLogger(__name__)

class SurveyView(LoginRequiredMixin, View):
    model = Survey
    fields = ('name', 'language', 'prompt_type')

    def get_success_url(self, **kwargs):
        return self.object.get_prompt_url()
        return reverse_lazy('survey-prompts', args = (self.object.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get('project'):
            context['project'] = Project.objects.get(id=self.request.GET.get('project'))
        return context

    def get_initial(self):
        initial = super().get_initial()
        # context = self.get_context_data(**kwargs)
        if self.request.GET.get('project'):
            initial['project'] = Project.objects.get(id=self.request.GET.get('project'))
        return initial.copy()

class SurveyList(SurveyView, ListView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 100
        return context

    def get_queryset(self):
        queryset = super(SurveyList, self).get_queryset()
        if self.request.GET.get('project'):
            queryset = queryset.filter(project=Project.objects.get(id=self.request.GET.get('project')))
        return queryset

class Home(ListView):
    model = Country
    template_name = 'surveys/home.html'

class SurveyDetail(SurveyView, DetailView):

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def post(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        client = self.get_twilio_client()
        for contact in self.object.respondents.all():
            self.voice_survey(request, contact, client, self.object)
        messages.success(request, 'Message successfuly sent')
        return self.render_to_response(context=context)

    def get_twilio_client(self):
        return TwilioClient(
            settings.TWILIO_ACCOUNT_SID, 
            settings.TWILIO_AUTH_TOKEN
        )

    def voice_survey(self, request, contact, client, survey):
        request.session['contact_id'] = contact.id
        call = client.calls.create(
            # machine_detection='Enable',
            to=contact.phone,
            from_='+14152956702',
            url=request.build_absolute_uri(
                reverse('run-survey', kwargs={'pk':survey.id})
            )
        )
        return True

    def sms_survey(self, request, contact):
        message = client.messages.create(
            body=request.POST.get('body'),
            from_='+14152956702',
            to=contact
        )
        return True

@csrf_exempt
@validate_twilio_request
def run_survey(request, pk):
    survey = Survey.objects.get(id=pk)
    first_question = survey.first_question
    first_question_id = {
        'pk': survey.id,
        'question_pk': first_question.id
    }
    first_question_url = reverse('run-question', kwargs=first_question_id)
    twiml_response = VoiceResponse()
    twiml_response = survey.say_prompt(twiml=twiml_response, kind='welcome')
    # logger.info(twiml_response)
    twiml_response.redirect(first_question_url, method='GET')
    messages.success(request, 'Survey Sent')
    return HttpResponse(twiml_response, content_type='application/xml')


@require_GET
@validate_twilio_request
def run_question(request, pk, question_pk):
    question = Question.objects.get(id=question_pk)
    twiml_response = VoiceResponse()
    action = save_response_url(question)
    if question.kind == Question.TEXT:
        twiml_response = question.say_question_and_prompt(twiml_response)
        twiml_response.record(
            action=action,
            method='POST',
            max_length=10,
            transcribe=True,
            transcribe_callback=action
        )
    else:
        gather = Gather(action=action, method='POST', numDigits=1)
        gather = question.say_question_and_prompt(gather)
        twiml_response.append(gather)

    request.session['answering_question_id'] = question.id
    return HttpResponse(twiml_response, content_type='application/xml')

def save_response_url(question):
    return reverse('save_response',
                   kwargs={'pk': question.survey.id,
                           'question_pk': question.id})


@require_POST
@validate_twilio_request
def redirects_twilio_request_to_proper_endpoint(request):
    answering_question = request.session.get('answering_question_id')
    if not answering_question:
        first_survey = Survey.objects.first()
        redirect_url = reverse('survey',
                               kwargs={'survey_id': first_survey.id})
    else:
        question = Question.objects.get(id=answering_question)
        redirect_url = reverse('save_response',
                               kwargs={'pk': question.survey.id,
                                       'question_pk': question.id})
    return HttpResponseRedirect(redirect_url)

@require_POST
@csrf_exempt
@validate_twilio_request
def save_response(request, pk, question_pk):
    question = Question.objects.get(id=question_pk)
    save_response_from_request(request, question)
    next_question = question.next()
    if not next_question:
        return goodbye(request, question.survey)
    else:
        return next_question_redirect(next_question.id, pk)

def next_question_redirect(question_pk, pk):
    parameters = {'pk': pk, 'question_pk': question_pk}
    question_url = reverse('question', kwargs=parameters)
    twiml_response = MessagingResponse()
    twiml_response.redirect(url=question_url, method='GET')
    return HttpResponse(twiml_response)

def goodbye(request, survey):
    # goodbye_messages = ['That was the last question',
    #                     'Thank you for taking this survey',
    #                     'Good-bye']
    # if request.is_sms:
    #     response = MessagingResponse()
    #     [response.message(message) for message in goodbye_messages]
    # else:
    response = VoiceResponse()
    response = survey.say_prompt(twiml=response, kind='goodbye')
    # [response.say(message) for message in goodbye_messages]
    response.hangup()

    return HttpResponse(response)

def save_response_from_request(request, question):
    # session_id = request.POST['MessageSid' if request.is_sms else 'CallSid']

    session_id = request.POST['CallSid']
    request_body = _extract_request_body(request, question.kind)
    phone_number = request.POST['To']
    response = QuestionResponse.objects.filter(question_id=question.id,
                                               call_sid=session_id).first()
    if not response:
        QuestionResponse(call_sid=session_id,
                         phone_number=phone_number,
                         contact=Contact.objects.filter(survey=question.survey, phone=phone_number)[0],
                         response=request_body,
                         question=question).save()
    else:
        response.response = request_body
        response.save()
    if 'TranscriptionText' in request.POST:
        response.transcription = request.POST.get('TranscriptionText')
        response.save()

def _extract_request_body(request, question_kind):
    Question.validate_kind(question_kind)

    # if request.is_sms:
    #     key = 'Body'
    # elif question_kind in [Question.YES_NO, Question.NUMERIC]:
    if question_kind in [Question.YES_NO, Question.NUMERIC]:
        key = 'Digits'
    # elif 'TranscriptionText' in request.POST:
    #     key = 'TranscriptionText'
    else:
        key = 'RecordingUrl'
    return request.POST.get(key)

class SurveyCreate(SurveyView, CreateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 50
        return context

    def form_valid(self, form):
        if self.request.GET.get('project'):
            form.instance.project = Project.objects.get(id=self.request.GET.get('project'))
            form.instance.save()
            for contact in form.instance.project.contact_set.all():
                form.instance.respondents.add(contact)
        return super().form_valid(form)

class SurveyUpdate(SurveyView, UpdateView):
    pass

class SurveyPrompts(SurveyUpdate):
    fields = None
    form_class = SurveyForm
    # template_name = 'surveys/survey_prompts.html'

    def get_success_url(self, **kwargs):
        return reverse_lazy('question-create', args = (self.object.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 50
        return context

class SurveyPromptSound(SurveyDetail):
    template_name = 'surveys/prompt_sound.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['formset'] = PromptFormSet(
            queryset=Prompt.objects.none(),
            initial=self.get_initial_categories(),
        )
        return context

    def get_initial_categories(self):
        categories = []
        for choice in Prompt.CATEGORY_CHOICES:
            categories.append({'category': choice[0], 'language': self.object.language})
        return categories

    def post(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        context['formset'] = self.get_formset(request)
        if context['formset'].is_valid():
            survey = self.process_formset(request, context['formset'])
            return redirect(reverse_lazy('question-create', kwargs = {'pk': survey.id}))
        messages.error(request, 'Please correct the errors below')
        return self.render_to_response(context=context)

    def get_formset(self, request):
        return PromptFormSet(
                            request.POST, 
                            request.FILES,
                            queryset=Prompt.objects.none(),
                            initial=self.get_initial_categories())

    def process_formset(self, request, formset):
        prompts = formset.save()
        self.object.add_prompts(prompts)
        messages.success(request, 'Prompts successfuly added')
        return self.object

class SurveyResponse(SurveyView, DetailView):
    template_name = 'surveys/survey_results.html'

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context
    
class QuestionView(LoginRequiredMixin, View):
    model = Question
    fields = ('body', 'kind', 'sound_file')

    def get_object(self, queryset=None):
        obj = Question.objects.get(id=self.kwargs['question_pk'])
        return obj

    def get_success_url(self, **kwargs):         
        return reverse_lazy('question-create', kwargs = {'pk': self.object.survey.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['survey'] = Survey.objects.get(id=self.kwargs['pk'])
        if getattr(context['survey'], 'project', None):
            context['project'] = context['survey'].project
        return context


class QuestionList(QuestionView, ListView):
    pass

class QuestionDetail(QuestionView, DetailView):
    pass

class QuestionCreate(QuestionView, CreateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 75
        return context

    def get_initial(self):
        initial = super(QuestionCreate, self).get_initial()
        # context = self.get_context_data(**kwargs)
        initial['survey'] = Survey.objects.get(id=self.kwargs['pk'])
        return initial.copy()

    def form_valid(self, form):
        form.instance.survey = Survey.objects.get(id=self.kwargs['pk'])
        return super().form_valid(form)

class QuestionUpdate(QuestionView, UpdateView):
    pass

class QuestionSound(QuestionView, UpdateView):
    template_name = 'surveys/question_sound.html'

class QuestionDelete(QuestionView, DeleteView):

    def get_success_url(self):
        return reverse_lazy('survey-detail', kwargs={'pk':self.kwargs['pk']})

class ProjectView(LoginRequiredMixin, View):
    model = Project
    fields = ('name', 'country', 'description')

class ProjectList(ProjectView, ListView):
    pass

class ProjectDetail(ProjectView, DetailView):
    pass

class ProjectCreate(ProjectView, CreateView):

    def get_success_url(self, **kwargs):
        print(self.request.POST)     
        return reverse_lazy('contact-add', args = (self.object.slug,))

    def get_initial(self):
        initial = super().get_initial()
        # context = self.get_context_data(**kwargs)
        if self.request.GET.get('country'):
            initial['country'] = Country.objects.get(id=self.request.GET.get('country'))
        return initial.copy()

    def form_valid(self, form):
        for field in Project.objects.get_function_fields():
            setattr(form.instance, field, self.request.POST.get(field))
        form.instance.save()
        return super().form_valid(form)

class ProjectUpdate(ProjectView, UpdateView):
    pass

class ContactView(LoginRequiredMixin, View):
    model = Contact
    fields = ('first_name', 'last_name', 'phone', 'email')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get('survey'):
            context['survey'] = Survey.objects.get(id=self.request.GET.get('survey'))
        if self.request.GET.get('project'):
            context['project'] = Project.objects.get(id=self.request.GET.get('project'))
        return context


class ContactList(ContactView, ListView):
    pass

class ContactDetail(ContactView, DetailView):
    
    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        if self.request.GET.get('survey'):
            context['survey'] = Survey.objects.get(id=self.request.GET.get('survey'))
            context['responses'] = QuestionResponse.objects.filter(question__survey=context['survey'], contact=self.object)
        return context

class ContactCreate(ContactView, CreateView):

    def get_success_url(self):
        return reverse_lazy('contact-create') + '?project={}'.format(self.request.GET.get('project'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 25
        return context

    def get_initial(self):
        initial = super().get_initial()
        # context = self.get_context_data(**kwargs)
        if self.request.GET.get('project'):
            initial['project'] = Project.objects.get(id=self.request.GET.get('project'))
        return initial.copy()

    def form_valid(self, form):
        if self.request.GET.get('project'):
            form.instance.project = Project.objects.get(id=self.request.GET.get('project'))
            self.add_project_contacts_to_surveys(form.instance.project)
        return super().form_valid(form)

    def add_project_contacts_to_surveys(self, project):
        for survey in project.survey_set.all():
            survey.respondents.add(*project.contact_set.all())
            survey.save()
        return True


class ContactUpdate(ContactView, UpdateView):
    pass

class ContactAdd(ProjectDetail):
    template_name = 'surveys/contact_add.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 25
        return context

class ContactImport(ProjectDetail):
    template_name = 'surveys/contact_import.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 25
        return context

    def post(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        try:
            import_file = request.FILES['csv_file']
        except KeyError:
            messages.error(request, 'Please upload a file.')
        else: 
            self.import_csv_data(import_file)
        return redirect(reverse('survey-create')+'?project={}'.format(self.object.id))
        # return redirect(reverse('contact-list') + '?project={}'.format(self.object.id))

    def import_csv_data(self, import_file):
        errors = []
        try:
            # with open(import_file, 'rt', encoding="utf-8", errors='ignore') as csvfile:
            reader = csv.DictReader(io.StringIO(import_file.read().decode('utf-8')))
        except Exception as error:
            errors.append(error)
            messages.error(self.request, \
                'Failed to read file. Please make sure the file is in CSV format.')
        else:
            errors = self.enumerate_rows(reader)
        return errors

    # Loop through CSV, skipping header row.
    def enumerate_rows(self, reader, start=2):
        # Index is for row numbers in error message-s.
        for index, contact in enumerate(reader, start=2):
            row_errors = []
            try:
                self.import_contact_row(contact)
            except Exception as error:
                row_errors.append('Row {0}: {1}'.format(index, error))
        return row_errors

    def import_contact_row(self, contact_dict):
        contact = Contact.objects.create(**contact_dict)
        return contact

class ContactRemove(ContactDetail):

    def get(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        survey = Survey.objects.get(id=request.GET.get('survey'))
        survey.respondents.remove(self.object)
        messages.error(request, 'Contact removed from survey')
        return redirect(reverse('survey-detail', kwargs={'pk':survey.id}))


class QuestionResponseView(LoginRequiredMixin, View):
    model = QuestionResponse

class QuestionResponseList(QuestionResponseView, ListView):
    pass

class QuestionResponseDetail(QuestionResponseView, DetailView):
    pass

class PromptView(LoginRequiredMixin, View):
    template_name = 'surveys/survey_form.html'
    model = Prompt
    fields = ('name', 'language', 'category', 'sound_file')

class PromptList(PromptView, ListView):
    pass

class PromptDetail(PromptView, DetailView):
    pass

class PromptCreate(PromptView, CreateView):

    def post(self, request, **kwargs):
        survey = Survey.objects.get(id=request.POST['survey'])
        category = request.POST['category']
        prompt = Prompt.objects.create(
            name=request.POST['name'],
            category=category,
            language=survey.language,
        )
        setattr(survey, '{}_prompt'.format(category), prompt)
        return HttpResponse(prompt.id)

    def form_valid(self, form):
        print(form)
        return super().form_valid(form)

class PromptUpdate(PromptView, UpdateView):
    pass

