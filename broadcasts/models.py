from django.db import models
from base_site.models import Language, Project, Contact
from django.urls import reverse
from zwazo.storage_backends import PrivateMediaStorage

class Broadcast(models.Model):
    VOICE = 'voice'
    SMS = 'SMS'
    BOTH = 'Both'

    BROADCAST_CHOICES = (
        (VOICE, 'Voice'),
        (SMS, 'SMS'),
        (BOTH, 'Both'),
    )

    name = models.CharField(max_length=255)
    broadcast_type = models.CharField(max_length=30, choices=BROADCAST_CHOICES, default=VOICE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    respondents = models.ManyToManyField(Contact, blank=True)
    is_callback = models.BooleanField(default=False)
    text = models.CharField(max_length=255, blank=True)
    sound_file = models.FileField(storage=PrivateMediaStorage(), upload_to='files/', blank=True, null=True)
    repeater = models.CharField(max_length=2, blank=True)
    response = models.CharField(max_length=2, blank=True)
    max_length = models.IntegerField(default=1)
    timeout = models.IntegerField(default=5)    


    # @property
    # def first_question(self):
    #     return Question.objects.filter(broadcast__id=self.id
    #                                    ).order_by('id').first()
    def __str__(self):
        return '%s' % self.name

    # def get_absolute_url(self):
    #     return reverse('broadcast:broadcast-detail', kwargs={'pk':self.id})

    # def get_prompt_url(self):
    #     if self.prompt_type == self.TEXT:
    #         return reverse('broadcast:broadcast-prompts', kwargs={'pk':self.id})
    #     elif self.prompt_type == self.SOUND:
    #         return reverse('broadcast:broadcast-prompt-sound', kwargs={'pk':self.id}) 
    #     else:
    #         self.add_prompts(prompts=Prompt.objects.filter(is_default=True))
    #         return reverse('broadcast:question-create', kwargs={'pk':self.id})  

    # def add_prompts(self, prompts):
    #     for prompt in prompts:
    #         setattr(self, '{}_prompt'.format(prompt.category), prompt)
    #     self.save()
    #     return self

    # def get_prompt(self, kind):
    #     prompt = getattr(self, '{}_prompt'.format(kind))
    #     # prompt = getattr(self, '{}_prompt'.format(self.kind.replace('-','_')))
    #     return prompt.get_twiml_data(self.prompt_type)

    def say_message(self, twiml, kind):
        verb, args, kwargs = self.get_message(sound_file=sound_file)
        getattr(twiml, verb)(*args, **kwargs)
        return twiml
