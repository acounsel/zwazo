from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import View, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Gather, Dial, VoiceResponse, Say

from .models import Language, Country, Project, Contact
from .models import Survey, Question, QuestionResponse
from .decorators import validate_twilio_request

class SurveyView(View):
    model = Survey
    fields = ('name', 'language', 'project', 'respondents')

    def get_success_url(self, **kwargs):         
        return reverse_lazy('question-create', args = (self.object.id,))

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

    def get_queryset(self):
        queryset = super(SurveyList, self).get_queryset()
        if self.request.GET.get('project'):
            queryset = queryset.filter(project=Project.objects.get(id=self.request.GET.get('project')))
        return queryset

class Home(SurveyList):
    template_name = 'surveys/home.html'

class SurveyDetail(SurveyView, DetailView):

    def post(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        client = self.get_twilio_client()
        print(self.object.respondents.all())
        for contact in self.object.respondents.all():
            print(contact)
            self.voice_survey(request, contact, client, self.object)
        messages.success(request, 'Message successfuly sent')
        return self.render_to_response(context=context)

    def get_twilio_client(self):
        return TwilioClient(
            settings.TWILIO_ACCOUNT_SID, 
            settings.TWILIO_AUTH_TOKEN
        )

    def voice_survey(self, request, contact, client, survey):
        call = client.calls.create(
            to=contact,
            from_='+14152956702',
            url=request.build_absolute_uri(
                reverse('run-survey', kwargs={'pk':survey.id})
            )
        )
        print(call)
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
def run_survey(self, request, pk):
    survey = Survey.objects.get(id=pk)
    first_question = survey.first_question
    first_question_id = {
        'pk': first_question.id
    }
    first_question_url = reverse('run-question', kwargs=first_question_id)
    welcome = 'Hello and thank you for taking the %s survey' % survey.name
    twiml_response = VoiceResponse()
    twiml_response.say(welcome)
    twiml_response.redirect(first_question_url, method='GET')

    return HttpResponse(twiml_response, content_type='application/xml')


@require_GET
@validate_twilio_request
def run_question(request, pk):
    question = Question.objects.get(id=pk)
    twiml_response = VoiceResponse()

    twiml_response.say(question.body)
    twiml_response.say(VOICE_INSTRUCTIONS[question.kind])

    action = save_response_url(question)
    if question.kind == Question.TEXT:
        twiml_response.record(
            action=action,
            method='POST',
            max_length=6,
            transcribe=True,
            transcribe_callback=action
        )
    else:
        twiml_response.gather(action=action, method='POST')

    request.session['answering_question_id'] = question.id
    return HttpResponse(twiml_response, content_type='application/xml')

VOICE_INSTRUCTIONS = {
    Question.TEXT: 'Please record your answer after the beep and then hit the pound sign',
    Question.YES_NO: 'Please press the one key for yes and the zero key for no and then hit the pound sign',
    Question.NUMERIC: 'Please press a number between 1 and 10 and then hit the pound sign'
}

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
                               kwargs={'survey_id': question.survey.id,
                                       'question_id': question.id})
    return HttpResponseRedirect(redirect_url)

@require_POST
@validate_twilio_request
def save_response(request, survey_id, question_id):
    question = Question.objects.get(id=question_id)

    save_response_from_request(request, question)

    next_question = question.next()
    if not next_question:
        return goodbye(request)
    else:
        return next_question_redirect(next_question.id, survey_id)

def next_question_redirect(question_id, survey_id):
    parameters = {'survey_id': survey_id, 'question_id': question_id}
    question_url = reverse('question', kwargs=parameters)

    twiml_response = MessagingResponse()
    twiml_response.redirect(url=question_url, method='GET')
    return HttpResponse(twiml_response)

def goodbye(request):
    goodbye_messages = ['That was the last question',
                        'Thank you for taking this survey',
                        'Good-bye']
    # if request.is_sms:
    #     response = MessagingResponse()
    #     [response.message(message) for message in goodbye_messages]
    # else:
    response = VoiceResponse()
    [response.say(message) for message in goodbye_messages]
    response.hangup()

    return HttpResponse(response)

def save_response_from_request(request, question):
    # session_id = request.POST['MessageSid' if request.is_sms else 'CallSid']
    session_id = request.POST['CallSid']
    request_body = _extract_request_body(request, question.kind)
    phone_number = request.POST['From']

    response = QuestionResponse.objects.filter(question_id=question.id,
                                               call_sid=session_id).first()
    if not response:
        QuestionResponse(call_sid=session_id,
                         phone_number=phone_number,
                         response=request_body,
                         question=question).save()
    else:
        response.response = request_body
        response.save()

def _extract_request_body(request, question_kind):
    Question.validate_kind(question_kind)

    # if request.is_sms:
    #     key = 'Body'
    # elif question_kind in [Question.YES_NO, Question.NUMERIC]:
    if question_kind in [Question.YES_NO, Question.NUMERIC]:
        key = 'Digits'
    elif 'TranscriptionText' in request.POST:
        key = 'TranscriptionText'
    else:
        key = 'RecordingUrl'

    return request.POST.get(key)

class SurveyCreate(SurveyView, CreateView):
    pass

class SurveyUpdate(SurveyView, UpdateView):
    pass

class QuestionView(View):
    model = Question
    fields = ('body', 'kind', 'sound', 'survey')

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

    def get_initial(self):
        initial = super(QuestionCreate, self).get_initial()
        # context = self.get_context_data(**kwargs)
        initial['survey'] = Survey.objects.get(id=self.kwargs['pk'])
        return initial.copy()

class QuestionUpdate(QuestionView, UpdateView):
    pass

class ProjectView(View):
    model = Project
    fields = ('name', 'country', 'description')

class ProjectList(ProjectView, ListView):
    pass

class ProjectDetail(ProjectView, DetailView):
    pass

class ProjectCreate(ProjectView, CreateView):
    pass

class ProjectUpdate(ProjectView, UpdateView):
    pass

class ContactView(View):
    model = Contact
    fields = ('first_name', 'last_name', 'project', 'phone', 'email')

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
    pass

class ContactCreate(ContactView, CreateView):

    def get_initial(self):
        initial = super().get_initial()
        # context = self.get_context_data(**kwargs)
        if self.request.GET.get('project'):
            initial['project'] = Project.objects.get(id=self.request.GET.get('project'))
        return initial.copy()

    def form_valid(self, form):
        if form.instance.project:
            self.add_project_contacts_to_surveys(form.instance.project)
        return super().form_valid(form)

    def add_project_contacts_to_surveys(self, project):
        for survey in project.survey_set.all():
            survey.respondents.add(*project.contact_set.all())
            survey.save()
        return True


class ContactUpdate(ContactView, UpdateView):
    pass

class QuestionResponseView(View):
    model = QuestionResponse

class QuestionResponseList(QuestionResponseView, ListView):
    pass

class QuestionResponseDetail(QuestionResponseView, DetailView):
    pass


