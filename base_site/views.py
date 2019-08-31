import csv
import io
import logging
from django.shortcuts import render
from django.views.generic import View, DetailView, ListView, CreateView, UpdateView, TemplateView
from .models import Country, Project, Contact
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from broadcasts.models import Broadcast
from surveys.models import Survey, QuestionResponse as SurveyQuestionResponse
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Gather, Dial, VoiceResponse, Say
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect


@csrf_exempt
def voice_response(request):
    if Survey.objects.filter(is_callback=True).count():
        callback_response = Survey.objects.get(is_callback=True)
        first_question = callback_response.first_question
        first_question_id = {
            'pk': callback_response.id,
            'question_pk': first_question.id
        }
        first_question_url = reverse('run-question', kwargs=first_question_id)
        twiml_response = VoiceResponse()
        twiml_response = callback_response.say_prompt(twiml=twiml_response, kind='welcome')
        # logger.info(twiml_response)
        twiml_response.redirect(first_question_url, method='GET')
        return HttpResponse(twiml_response, content_type='application/xml') 

    elif Broadcast.objects.filter(is_callback=True).count():
        callback_response = Broadcast.objects.get(is_callback=True)
        twiml_response = VoiceResponse()
        twiml_response.play(callback_response.sound_file.url)
        # logger.info(twiml_response)
        messages.success(request, 'Playback Successful')
        return HttpResponse(str(twiml_response), content_type='application/xml')


class Home(ListView):
    model = Country
    template_name = 'base_site/home.html'

class ProjectView(LoginRequiredMixin, View):
    model = Project
    fields = ('name', 'country', 'description')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CommunicationCreate(TemplateView):
    model = Project
    template_name = 'base_site/communication_create.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = Project.objects.get(slug=context['slug'])
        return context

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
    model = Contact
    template_name = 'base_site/contact-list.html'
    context_object_name = 'contacts'

    def get_queryset(self):
        queryset = super(ContactList, self).get_queryset()
        print(queryset)
        print(self.request)
        return queryset.filter(project=self.request.GET.get('project'))

class ContactDetail(ContactView, DetailView):
    
    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        if self.request.GET.get('survey'):
            context['survey'] = Survey.objects.get(id=self.request.GET.get('survey'))
            context['responses'] = SurveyQuestionResponse.objects.filter(question__survey=context['survey'], contact=self.object)
        elif self.request.GET.get('broadcast'):
            context['broadcast'] = Broadcast.objects.get(id=self.request.GET.get('broadcast'))
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
            form.save()
            form.instance.project.add(Project.objects.get(id=self.request.GET.get('project')))
            self.add_project_contacts(form.instance.project)
        return super().form_valid(form)

    def add_project_contacts(self, project):
        for broadcast in Broadcast.objects.filter(project=project.name):
            broadcast.respondents.add(*project.contact_set.all())
            broadcast.save()
        for survey in Survey.objects.filter(project=project.name):
            survey.respondents.add(*project.contact_set.all())
            survey.save()
        return True


class ContactUpdate(ContactView, UpdateView):
    pass

class ContactAdd(ProjectDetail):
    template_name = 'base_site/contact_add.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 25
        return context

class ContactImport(ProjectDetail):
    template_name = 'base_site/contact_import.html'

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
        return redirect(reverse('contact-list')+'?project={}'.format(self.object.id))
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
        contact, created = Contact.objects.update_or_create(
            phone=contact_dict['phone'],
            first_name=contact_dict['first_name'],
            last_name=contact_dict['last_name'],
            defaults={
            'email': contact_dict["email"],
            })
        contact.project.add(self.object.id)
        return contact

class ContactRemove(ContactDetail):

    def get(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        if self.request.GET.get('survey'):
            survey = Survey.objects.get(id=request.GET.get('survey'))
            survey.respondents.remove(self.object)
            messages.error(request, 'Contact removed from survey')
            return redirect(reverse('survey-detail', kwargs={'pk':survey.id}))
        elif self.request.GET.get('broadcast'):
            broadcast = Broadcast.objects.get(id=request.GET.get('broadcast'))
            broadcast.respondents.remove(self.object)
            messages.error(request, 'Contact removed from broadcast')
            return redirect(reverse('broadcast:broadcast-detail', kwargs={'pk':broadcast.id}))


