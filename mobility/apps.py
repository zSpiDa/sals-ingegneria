from django.apps import AppConfig
class MobilityConfig(AppConfig):  # <-- Usa il nome reale della tua classe
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mobility'  # <-- Usa il nome reale della tua cartella app

    def ready(self):
        """
        Questo metodo viene eseguito una sola volta all'avvio di Django.
        Importando qui i segnali, indichiamo a Django di attivarli e metterli in ascolto.
        """
        # Sostituisci 'smart_mobility' con il nome reale della tua app se è diverso
        import mobility.signals