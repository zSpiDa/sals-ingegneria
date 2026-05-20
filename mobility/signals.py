from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Utente

@receiver(post_save, sender=User)
def gestisci_creazione_utente(sender, instance, created, **kwargs):
    """
    Segnale automatico (post_save): si attiva subito dopo il salvataggio di un User.
    Se l'utente è stato appena creato nel sistema (created=True), 
    Django genera automaticamente il profilo 'Utente' di Smart Mobility ad esso collegato.
    """
    if created:
        # Creiamo l'Utente associandolo all'istanza dell'User appena nato.
        # Assegniamo nome e cognome prendendoli dall'User standard (se presenti).
        Utente.objects.create(
            user=instance,
            nome=instance.first_name,
            cognome=instance.last_name
        )

@receiver(post_save, sender=User)
def salva_profilo_utente(sender, instance, **kwargs):
    """
    Questo assicura che se in futuro vengono modificati i dati base dell'User 
    (es. tramite pannello Admin), anche il relativo profilo Utente venga aggiornato e salvato.
    """
    if hasattr(instance, 'profilo_utente'):
        instance.profilo_utente.save()