from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, DetailView, ListView
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView
from .models import Broadcast
from surveys.models import Survey
from base_site.models import Project, Contact
from django.views.decorators.csrf import csrf_exempt
from surveys.decorators import validate_twilio_request
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse, reverse_lazy
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import Gather, Dial, VoiceResponse, Say
from django.contrib import messages
from django.shortcuts import render, redirect
from base_site.views import ContactList, ContactDetail, ContactView
from zwazo import settings
from django.http import HttpResponse, HttpResponseRedirect

class BroadcastView(LoginRequiredMixin, View):
    model = Broadcast
    fields = ('name', 'language', 'broadcast_type', 'text', 'sound_file', 'repeater', 'response', 'is_callback')

    def get_success_url(self, **kwargs):
        return reverse_lazy('broadcast:broadcast-detail', args = (self.object.id,))

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

class BroadcastList(BroadcastView, ListView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['setup_percent'] = 100
        return context

    def get_queryset(self):
        queryset = super(BroadcastList, self).get_queryset()
        if self.request.GET.get('project'):
            queryset = queryset.filter(project=Project.objects.get(id=self.request.GET.get('project')))
        return queryset

class BroadcastDetail(BroadcastView, DetailView):
    template_name='broadcasts/broadcast_detail.html'

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
            if self.object.sound_file:
                self.voice_broadcast(request, contact, client, self.object)
            if self.object.text:
                self.sms_broadcast(request, contact, client)
        messages.success(request, 'Broadcast successfuly sent')
        return self.render_to_response(context=context)

    def get_twilio_client(self):
        return TwilioClient(
            settings.TWILIO_ACCOUNT_SID, 
            settings.TWILIO_AUTH_TOKEN
        )

    def voice_broadcast(self, request, contact, client, broadcast):
        request.session['contact_id'] = contact.id
        call = client.calls.create(
            # machine_detection='Enable',
            to=contact.phone,
            from_='+14152956702',
            url=request.build_absolute_uri(
                reverse('broadcast:run-broadcast', kwargs={'pk':broadcast.id})
            )
        )
        return True

    def sms_broadcast(self, request, contact, client):
        message = client.messages.create(
            body=self.object.text,
            from_='+14152956702',
            to=contact.phone
        )
        return True

@csrf_exempt
@validate_twilio_request
def run_broadcast(request, pk):
    broadcast = Broadcast.objects.get(id=pk)
    twiml_response = VoiceResponse()
    twiml_response.play(broadcast.sound_file.url)
    # logger.info(twiml_response)
    messages.success(request, 'Broadcast Sent')
    return HttpResponse(str(twiml_response), content_type='application/xml')

def remove_callbacks():
    callback_surveys = Survey.objects.filter(is_callback=True)
    for survey in callback_surveys:
        survey.is_callback = False
        survey.save()
    callback_broadcasts = Broadcast.objects.filter(is_callback=True)
    for broadcast in callback_broadcasts:
        broadcast.is_callback = False
        broadcast.save() 

class BroadcastCreate(BroadcastView, CreateView):
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
        if form.instance.is_callback:
            remove_callbacks()
        return super().form_valid(form)

class BroadcastUpdate(BroadcastView, UpdateView):
    fields = ('name', 'language', 'broadcast_type', 'text', 'sound_file', 'repeater', 'response', 'is_callback')
    template_name_suffix = '_update_form'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=context['broadcast'].project.id)
        return context

    def get_success_url(self, **kwargs):
        return reverse_lazy('broadcast:broadcast-list') + '?project={}'.format(self.object.project.id)

    def form_valid(self, form):
        if form.instance.is_callback:
            remove_callbacks()
        return super().form_valid(form)

class BroadcastDelete(BroadcastView, DeleteView):
    def get_success_url(self):
        return reverse_lazy('broadcast:broadcast-list') + '?project={}'.format(self.object.project.id)

class BroadcastContactUpdate(BroadcastView, UpdateView):
    fields = ('respondents',)
    template_name_suffix = '_manage_contacts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact'] = Contact.objects.filter(project=self.object.project)
        return context        

    def get_form(self, form_class=None):    
        form = super(BroadcastContactUpdate, self).get_form(form_class)
        form.fields["respondents"].queryset = Contact.objects.filter(project=self.request.GET.get('project'))
        return form

    def get_success_url(self, **kwargs):
        return reverse_lazy('broadcast:broadcast-detail', args = (self.object.id,))

class ContactRemove(ContactDetail):

    def get(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        broadcast = Broadcast.objects.get(id=request.GET.get('broadcast'))
        broadcast.respondents.remove(self.object)
        messages.error(request, 'Contact removed from broadcast')
        return redirect(reverse('broadcast-detail', kwargs={'pk':broadcast.id}))

