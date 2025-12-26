from django.contrib import admin
from .models import Client, Chauffeur, Vehicule, Destination, TypeService, Tarification, Expedition, Tournee, TrackingExpedition, Facture, Paiement
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Sum

# ============================================
# SECTION 1 : Modèles de base
# ============================================
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'solde', 'solde']
    readonly_fields = ['solde']


class TrackingInline(admin.TabularInline):
    model = TrackingExpedition
    extra = 0
    readonly_fields = ['date_evenement', 'statut_etape', 'commentaire']


class ExpeditionAdmin(admin.ModelAdmin):
    readonly_fields = ['montant_total', 'date_livraison_prevue']
    inlines = [TrackingInline]


@admin.register(Tournee)
class TourneeAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        obj = kwargs.get('obj')
        
        vehicules_libres = Vehicule.objects.filter(statut='DISPONIBLE')
        chauffeurs_libres = Chauffeur.objects.filter(statut_disponibilite='DISPONIBLE')

        if obj:
            vehicules_libres |= Vehicule.objects.filter(id=obj.vehicule.id)
            chauffeurs_libres |= Chauffeur.objects.filter(id=obj.chauffeur.id)

        context['adminform'].form.fields['vehicule'].queryset = vehicules_libres
        context['adminform'].form.fields['chauffeur'].queryset = chauffeurs_libres
        
        return super().render_change_form(request, context, *args, **kwargs)


admin.site.register(Client)
admin.site.register(Chauffeur)
admin.site.register(Vehicule)
admin.site.register(TypeService)
admin.site.register(Tarification)
admin.site.register(Expedition, ExpeditionAdmin)
admin.site.register(TrackingExpedition)


class DestinationAdmin(admin.ModelAdmin):
    list_display = ['ville', 'wilaya', 'pays', 'zone_geographique', 'tarif_base']
    search_fields = ['ville', 'wilaya']

admin.site.register(Destination, DestinationAdmin)


# ============================================
# SECTION 3 : Facturation et Paiements
# ============================================


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0
    readonly_fields = ['numero_paiement', 'date_enregistrement']
    fields = [
        'numero_paiement', 'montant', 'methode_paiement', 
        'reference_paiement', 'date_paiement', 'statut', 'remarques'
    ]
    
    def has_delete_permission(self, request, obj=None):
        return False


class ExpeditionInline(admin.TabularInline):
    model = Expedition
    extra = 0
    readonly_fields = ['get_numero_expedition', 'montant_total', 'statut']
    fields = [
        'get_numero_expedition', 'destination', 'type_service',
        'poids', 'volume', 'montant_total', 'statut'
    ]
    
    def get_numero_expedition(self, obj):
        return obj.get_numero_expedition()
    get_numero_expedition.short_description = 'N° Expédition'
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = [
        'numero_facture', 'client', 'date_emission', 
        'montant_ttc_display', 'montant_paye_display', 
        'montant_restant_display', 'statut_badge', 
        'est_echue_badge'
    ]
    
    
    search_fields = [
        'numero_facture', 'client__nom', 'client__prenom',
        'client__telephone', 'remarques'
    ]
    
    readonly_fields = [
        'numero_facture', 'montant_ht', 'montant_tva', 
        'montant_ttc', 'montant_paye', 'montant_restant',
        'statut_paiement', 'date_emission', 'date_modification',
        'voir_client'
    ]
    
    fieldsets = (
        ('Informations Générales', {
            'fields': (
                'numero_facture', 'client', 'voir_client',
                'date_emission', 'date_echeance'
            )
        }),
        ('Montants', {
            'fields': (
                'montant_ht', 'taux_tva', 'montant_tva',
                'montant_ttc', 'montant_paye', 'montant_restant'
            ),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('statut_paiement', 'remarques')
        }),
        ('Dates', {
            'fields': ('date_modification',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ExpeditionInline, PaiementInline]
    
    date_hierarchy = 'date_emission'
    
    actions = ['marquer_comme_payee', 'generer_rappel']
    
    def montant_ttc_display(self, obj):
        return f"{obj.montant_ttc:,.2f} DA"
    montant_ttc_display.short_description = 'Montant TTC'
    
    def montant_paye_display(self, obj):
        return f"{obj.montant_paye:,.2f} DA"
    montant_paye_display.short_description = 'Payé'
    
    def montant_restant_display(self, obj):
        color = 'green' if obj.montant_restant == 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} DA</span>',
            color, f"{obj.montant_restant:,.2f}"
        )
    montant_restant_display.short_description = 'Reste'
    
    def statut_badge(self, obj):
        colors = {
            'IMPAYEE': '#dc3545',
            'PARTIELLEMENT_PAYEE': '#ffc107',
            'PAYEE': '#28a745',
            'ANNULEE': '#6c757d'
        }
        color = colors.get(obj.statut_paiement, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_paiement_display()
        )
    statut_badge.short_description = 'Statut'
    
    def est_echue_badge(self, obj):
        if obj.est_echue():
            return format_html(
                '<span style="background-color: {}; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
                '#dc3545', '⚠ ÉCHUE'
            )
        return format_html('<span style="color: {};">{}</span>', 'green', '✓ OK')
    est_echue_badge.short_description = 'Échéance'
    
    def voir_client(self, obj):
        url = reverse('admin:app1_client_change', args=[obj.client.id])
        return format_html('<a href="{}">📋 Voir le client</a>', url)
    voir_client.short_description = 'Client'
    
    def marquer_comme_payee(self, request, queryset):
        count = 0
        for facture in queryset:
            if facture.statut_paiement != 'PAYEE':
                Paiement.objects.create(
                    facture=facture,
                    montant=facture.montant_restant,
                    methode_paiement='AUTRE',
                    remarques='Marqué comme payé par admin',
                    agent=request.user
                )
                count += 1
        self.message_user(request, f'{count} facture(s) marquée(s) comme payée(s)')
    marquer_comme_payee.short_description = '✓ Marquer comme payée'
    
    def generer_rappel(self, request, queryset):
        count = queryset.filter(statut_paiement__in=['IMPAYEE', 'PARTIELLEMENT_PAYEE']).count()
        self.message_user(request, f'Rappel généré pour {count} facture(s)')
    generer_rappel.short_description = '✉️ Générer rappel de paiement'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('client')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = [
        'numero_paiement', 'facture_link', 'client_nom',
        'montant_display', 'methode_paiement', 
        'date_paiement', 'statut_badge', 'agent'
    ]
    
    
    search_fields = [
        'numero_paiement', 'reference_paiement',
        'facture__numero_facture', 'facture__client__nom',
        'facture__client__prenom', 'remarques'
    ]
    
    readonly_fields = [
        'numero_paiement', 'date_enregistrement', 
        'date_modification', 'voir_facture'
    ]
    
    fieldsets = (
        ('Informations Générales', {
            'fields': (
                'numero_paiement', 'facture', 'voir_facture',
                'montant', 'date_paiement'
            )
        }),
        ('Méthode de Paiement', {
            'fields': (
                'methode_paiement', 'reference_paiement'
            )
        }),
        ('Statut et Agent', {
            'fields': ('statut', 'agent', 'remarques')
        }),
        ('Dates', {
            'fields': ('date_enregistrement', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'date_paiement'
    
    actions = ['valider_paiements', 'annuler_paiements']
    
    def facture_link(self, obj):
        url = reverse('admin:app1_facture_change', args=[obj.facture.id])
        return format_html('<a href="{}">{}</a>', url, obj.facture.numero_facture)
    facture_link.short_description = 'N° Facture'
    
    def client_nom(self, obj):
        return obj.facture.client
    client_nom.short_description = 'Client'
    
    def montant_display(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: green;">{} DA</span>',
            f"{obj.montant:,.2f}"
        )
    montant_display.short_description = 'Montant'
    
    def statut_badge(self, obj):
        colors = {
            'VALIDE': '#28a745',
            'EN_ATTENTE': '#ffc107',
            'ANNULE': '#dc3545'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def voir_facture(self, obj):
        url = reverse('admin:app1_facture_change', args=[obj.facture.id])
        return format_html('<a href="{}">📋 Voir la facture</a>', url)
    voir_facture.short_description = 'Facture'
    
    def valider_paiements(self, request, queryset):
        count = queryset.filter(statut='EN_ATTENTE').update(statut='VALIDE')
        self.message_user(request, f'{count} paiement(s) validé(s)')
    valider_paiements.short_description = '✓ Valider les paiements'
    
    def annuler_paiements(self, request, queryset):
        count = 0
        for paiement in queryset.filter(statut='VALIDE'):
            paiement.annuler()
            count += 1
        self.message_user(request, f'{count} paiement(s) annulé(s)')
    annuler_paiements.short_description = '✗ Annuler les paiements'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('facture', 'facture__client', 'agent')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.agent = request.user
        super().save_model(request, obj, form, change)

from .models import Incident, Reclamation

# ============================================
# SECTION 4 : Incidents
# ============================================

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        'numero_incident', 'type_incident', 'gravite', 'statut',
        'expedition', 'tournee', 'date_incident', 'statut_badge'
    ]
    
    search_fields = [
        'numero_incident', 'titre', 'description',
        'expedition__client__nom', 'lieu_incident'
    ]
    
    readonly_fields = [
        'numero_incident', 'date_creation', 'date_resolution',
        'alerte_client_envoyee', 'alerte_direction_envoyee'
    ]
    
    fieldsets = (
        ('Informations Générales', {
            'fields': (
                'numero_incident', 'type_incident', 'gravite',
                'titre', 'description', 'lieu_incident'
            )
        }),
        ('Relations', {
            'fields': ('expedition', 'tournee')
        }),
        ('Dates', {
            'fields': (
                'date_incident', 'date_creation', 'date_resolution'
            )
        }),
        ('Gestion', {
            'fields': (
                'statut', 'agent_rapporteur', 'agent_responsable',
                'actions_entreprises', 'solution'
            )
        }),
        ('Impacts', {
            'fields': ('cout_estime', 'document')
        }),
        ('Alertes', {
            'fields': (
                'alerte_client_envoyee', 'alerte_direction_envoyee'
            ),
            'classes': ('collapse',)
        }),
        ('Remarques', {
            'fields': ('remarques',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'date_incident'
    
    actions = ['marquer_comme_resolu', 'envoyer_alerte_direction']
    
    def statut_badge(self, obj):
        colors = {
            'OUVERT': '#dc3545',
            'EN_COURS': '#ffc107',
            'RESOLU': '#28a745',
            'CLOS': '#6c757d'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def marquer_comme_resolu(self, request, queryset):
        count = queryset.exclude(statut='RESOLU').update(statut='RESOLU')
        self.message_user(request, f'{count} incident(s) marqué(s) comme résolu(s)')
    marquer_comme_resolu.short_description = '✓ Marquer comme résolu'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.agent_rapporteur = request.user
        super().save_model(request, obj, form, change)


# ============================================
# SECTION 5 : Réclamations
# ============================================

@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = [
        'numero_reclamation', 'client', 'nature', 'priorite',
        'statut_badge', 'date_reclamation', 'delai_badge',
        'agent_responsable'
    ]
    
    search_fields = [
        'numero_reclamation', 'objet', 'description',
        'client__nom', 'client__prenom'
    ]
    
    readonly_fields = [
        'numero_reclamation', 'date_reclamation',
        'date_modification', 'date_resolution', 'delai_traitement_display'
    ]
    
    fieldsets = (
        ('Informations Générales', {
            'fields': (
                'numero_reclamation', 'client', 'nature',
                'objet', 'description', 'priorite'
            )
        }),
        ('Relations', {
            'fields': ('expedition', 'facture', 'incident')
        }),
        ('Dates', {
            'fields': (
                'date_reclamation', 'date_modification',
                'date_resolution', 'delai_traitement_display'
            )
        }),
        ('Traitement', {
            'fields': (
                'statut', 'agent_responsable', 'reponse',
                'actions_correctives'
            )
        }),
        ('Compensation', {
            'fields': (
                'compensation_accordee', 'montant_compensation',
                'type_compensation'
            ),
            'classes': ('collapse',)
        }),
        ('Satisfaction Client', {
            'fields': ('client_satisfait',),
            'classes': ('collapse',)
        }),
        ('Documents et Remarques', {
            'fields': ('document', 'remarques'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'date_reclamation'
    
    actions = ['marquer_comme_resolue', 'assigner_a_moi']
    
    def statut_badge(self, obj):
        colors = {
            'NOUVELLE': '#dc3545',
            'EN_COURS': '#ffc107',
            'EN_ATTENTE_CLIENT': '#17a2b8',
            'RESOLUE': '#28a745',
            'REJETEE': '#6c757d',
            'ANNULEE': '#6c757d'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def delai_badge(self, obj):
        delai = obj.delai_traitement()
        if obj.est_en_retard():
            return format_html(
                '<span style="color: red; font-weight: bold;">{} jours ⚠</span>',
                delai
            )
        return format_html('<span style="color: green;">{} jours</span>', delai)
    delai_badge.short_description = 'Délai'
    
    def delai_traitement_display(self, obj):
        return f"{obj.delai_traitement()} jours"
    delai_traitement_display.short_description = 'Délai de traitement'
    
    def marquer_comme_resolue(self, request, queryset):
        count = queryset.exclude(statut='RESOLUE').update(statut='RESOLUE')
        self.message_user(request, f'{count} réclamation(s) marquée(s) comme résolue(s)')
    marquer_comme_resolue.short_description = '✓ Marquer comme résolue'
    
    def assigner_a_moi(self, request, queryset):
        count = queryset.update(agent_responsable=request.user)
        self.message_user(request, f'{count} réclamation(s) assignée(s) à vous')
    assigner_a_moi.short_description = '👤 M\'assigner ces réclamations'        