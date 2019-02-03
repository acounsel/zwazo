from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import View, DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Gather, Dial, VoiceResponse, Say

from .models import Language, Country, Project, Contact
from .models import Survey, Question, QuestionResponse

class SurveyList(ListView):
    model = Survey

class Home(SurveyList):
    template_name = 'surveys/home.html'

class SurveyView(View):
    model = Survey

class SurveyList(SurveyView, ListView):
    pass

class SurveyDetail(SurveyView, DetailView):

    def post(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        client = TwilioClient(account_sid, auth_token)
        contacts = request.POST.getlist('contact')
        for contact in contacts:
            if request.POST.get('voice'):
                call = client.calls.create(
                    to=contact,
                    from_='+14152956702',
                    url=request.build_absolute_uri(reverse('survey', kwargs={'survey_id':self.object.id}))
                )
            else:
                from_ = '+14152956702'
                message = client.messages.create(
                    body=request.POST.get('body'),
                    from_=from_,
                    to=contact
                )
        messages.success(request, 'Message successfuly sent')
        return self.render_to_response(context=context)

class SurveyCreate(SurveyView, CreateView):
    pass

class SurveyUpdate(SurveyView, UpdateView):
    pass

class ProjectView(View):
    model = Project
    fields = ('name', 'slug', 'country', 'description')

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

class ContactList(ContactView, ListView):
    pass

class ContactDetail(ContactView, DetailView):
    pass

class ContactCreate(ContactView, CreateView):
    pass

class ContactUpdate(ContactView, UpdateView):
    pass
