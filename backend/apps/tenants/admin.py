from datetime import date

from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

from .models import Plan, Subscription, Tenant


# ---------------------------------------------------------------------------
# Forms for intermediate action pages
# ---------------------------------------------------------------------------

class ChangeToEnterpriseForm(forms.Form):
    num_licencias = forms.IntegerField(
        min_value=1,
        label="Número de licencias",
        error_messages={"min_value": "El número de licencias debe ser mayor a cero."},
    )


class ExtendTrialForm(forms.Form):
    fecha_fin = forms.DateField(
        label="Nueva fecha de vencimiento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_fecha_fin(self):
        value = self.cleaned_data["fecha_fin"]
        if value <= date.today():
            raise forms.ValidationError("La fecha debe ser futura.")
        return value


class UpdateLicenseCountForm(forms.Form):
    num_licencias = forms.IntegerField(
        min_value=1,
        label="Número de licencias",
        error_messages={"min_value": "El número de licencias debe ser mayor a cero."},
    )


# ---------------------------------------------------------------------------
# TenantAdmin
# ---------------------------------------------------------------------------

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        "nombre_empresa",
        "get_subdominio",
        "get_plan_actual",
        "get_estado_acceso",
        "get_trial_expires_at",
        "get_num_licencias",
    ]
    list_filter = ["subscription__plan"]
    actions = ["change_to_enterprise"]

    def get_subdominio(self, obj):
        return obj.schema_name
    get_subdominio.short_description = "Subdominio"

    def get_plan_actual(self, obj):
        try:
            return obj.subscription.plan.nombre
        except Subscription.DoesNotExist:
            return "—"
    get_plan_actual.short_description = "Plan"

    def get_estado_acceso(self, obj):
        try:
            return "Activo" if obj.subscription.is_active() else "Bloqueado"
        except Subscription.DoesNotExist:
            return "—"
    get_estado_acceso.short_description = "Estado"

    def get_trial_expires_at(self, obj):
        try:
            return obj.subscription.fecha_fin or "—"
        except Subscription.DoesNotExist:
            return "—"
    get_trial_expires_at.short_description = "Vence el"

    def get_num_licencias(self, obj):
        try:
            n = obj.subscription.num_licencias
            return n if n is not None else "—"
        except Subscription.DoesNotExist:
            return "—"
    get_num_licencias.short_description = "Licencias"

    @admin.action(description="Cambiar a plan Enterprise")
    def change_to_enterprise(self, request, queryset):
        if request.POST.get("_apply"):
            form = ChangeToEnterpriseForm(request.POST)
            if form.is_valid():
                selected_ids = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
                targets = Tenant.objects.filter(pk__in=selected_ids).select_related(
                    "subscription__plan"
                )
                num_licencias = form.cleaned_data["num_licencias"]
                enterprise_plan = Plan.objects.get(nombre=Plan.ENTERPRISE)
                count = 0
                for tenant in targets:
                    sub = tenant.subscription
                    sub.plan = enterprise_plan
                    sub.fecha_fin = None
                    sub.num_licencias = num_licencias
                    sub.save()
                    count += 1
                self.message_user(
                    request,
                    f"{count} tenant(s) actualizados a Enterprise con {num_licencias} licencias.",
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = ChangeToEnterpriseForm()

        return TemplateResponse(
            request,
            "admin/tenants/change_to_enterprise.html",
            {
                "title": "Cambiar a Enterprise",
                "queryset": queryset,
                "form": form,
                "action_checkbox_name": admin.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )


# ---------------------------------------------------------------------------
# SubscriptionAdmin
# ---------------------------------------------------------------------------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "plan", "fecha_inicio", "fecha_fin", "num_licencias", "get_is_active"]
    list_filter = ["plan"]
    actions = ["extend_trial", "update_license_count"]

    def get_is_active(self, obj):
        return obj.is_active()
    get_is_active.short_description = "Activa"
    get_is_active.boolean = True

    @admin.action(description="Extender período de trial")
    def extend_trial(self, request, queryset):
        if request.POST.get("_apply"):
            form = ExtendTrialForm(request.POST)
            if form.is_valid():
                selected_ids = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
                targets = Subscription.objects.filter(pk__in=selected_ids)
                fecha_fin = form.cleaned_data["fecha_fin"]
                count = targets.update(fecha_fin=fecha_fin)
                self.message_user(
                    request,
                    f"Trial extendido hasta {fecha_fin} para {count} suscripción(es).",
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = ExtendTrialForm()

        return TemplateResponse(
            request,
            "admin/tenants/extend_trial.html",
            {
                "title": "Extender período de trial",
                "queryset": queryset,
                "form": form,
                "action_checkbox_name": admin.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )

    @admin.action(description="Actualizar número de licencias")
    def update_license_count(self, request, queryset):
        if request.POST.get("_apply"):
            form = UpdateLicenseCountForm(request.POST)
            if form.is_valid():
                selected_ids = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
                targets = Subscription.objects.filter(pk__in=selected_ids)
                num_licencias = form.cleaned_data["num_licencias"]
                count = targets.update(num_licencias=num_licencias)
                self.message_user(
                    request,
                    f"Número de licencias actualizado a {num_licencias} para {count} suscripción(es).",
                )
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = UpdateLicenseCountForm()

        return TemplateResponse(
            request,
            "admin/tenants/update_license_count.html",
            {
                "title": "Actualizar número de licencias",
                "queryset": queryset,
                "form": form,
                "action_checkbox_name": admin.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )
