from datetime import date, timedelta, datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, MonthArchiveView,
                                  TemplateView, YearArchiveView)
from stronghold.decorators import public

from .forms import IncidentCreateForm, IncidentUpdateCreateForm
from .models import Component, Incident, IncidentUpdate


def create_incident(request):
    if request.method == 'POST':
        form = IncidentCreateForm(request.POST)
        form2 = IncidentUpdateCreateForm(request.POST)
        if form.is_valid() and form2.is_valid():
            i = form.save(commit=False)
            i.user = request.user
            i.save()

            f = form2.save(commit=False)
            f.incident = i
            f.user = request.user
            f.save()
            return HttpResponseRedirect('/')
    else:
        form = IncidentCreateForm()
        form2 = IncidentUpdateCreateForm()

    return render_to_response('status/incident_create_form.html', {
        'form': form,
        'form2': form2,
    }, context_instance=RequestContext(request))


class DashboardView(ListView):
    model = Incident


class IncidentDeleteView(DeleteView):
    model = Incident

    def get_success_url(self):
        return reverse('status:dashboard')


class IncidentUpdateUpdateView(CreateView):
    model = IncidentUpdate
    form_class = IncidentUpdateCreateForm
    template_name = 'status/incident_form.html'

    def get_success_url(self):
        return reverse('status:incident_detail', args=[self.kwargs['pk']])

    def form_valid(self, form):
        i = form.save(commit=False)
        i.incident = Incident.objects.get(pk=self.kwargs['pk'])
        i.user = self.request.user
        i.save()
        return HttpResponseRedirect(self.get_success_url())


class IncidentDetailView(DetailView):
    model = Incident

    @method_decorator(public)
    def dispatch(self, *args, **kwargs):
        return super(IncidentDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IncidentDetailView, self).get_context_data(**kwargs)
        context.update({
            'form': IncidentUpdateCreateForm(),
        })
        return context


class IncidentArchiveYearView(YearArchiveView):
    make_object_list = True
    queryset = Incident.objects.all()
    date_field = 'updated'

    @method_decorator(public)
    def dispatch(self, *args, **kwargs):
        return super(IncidentArchiveYearView, self).dispatch(*args, **kwargs)


class IncidentArchiveMonthView(MonthArchiveView):
    make_object_list = True
    queryset = Incident.objects.all()
    date_field = 'updated'
    month_format = '%m'

    @method_decorator(public)
    def dispatch(self, *args, **kwargs):
        return super(IncidentArchiveMonthView, self).dispatch(*args, **kwargs)


class HomeView(TemplateView):
    http_method_names = ['get', ]
    template_name = 'status/home.html'

    @method_decorator(public)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        incident_list = Incident.objects.filter(updated__gt=date.today() - timedelta(days=7))
        incident_list = Incident.objects.filter(
            (Q(status__order=0) & Q(updated__gt=date.today() - timedelta(days=3))) | Q(status__order__gte=1)
        )
        context.update({
            'incident_list': incident_list
        })

        if hasattr(settings, 'STATUS_TICKET_URL'):
            context.update({'STATUS_TICKET_URL': settings.STATUS_TICKET_URL})

        if hasattr(settings, 'STATUS_LOGO_URL'):
            context.update({'STATUS_LOGO_URL': settings.STATUS_LOGO_URL})

        if hasattr(settings, 'STATUS_TITLE'):
            context.update({'STATUS_TITLE': settings.STATUS_TITLE})

        status_level = 'success'
        for incident in incident_list:
            try:
                if incident.get_latest_update().status.type == 'danger':
                    status_level = 'danger'
                    break
                elif incident.get_latest_update().status.type == 'warning':
                    status_level = 'warning'
                elif incident.get_latest_update().status.type == 'info' and not status_level == 'warning':
                    status_level = 'info'
            except AttributeError:
                # Unable to get_latest_update(), 'None' has no .status
                pass

        #BUG: This needs to be non-blocking
        for c in Component.objects.filter(updated__lte=datetime.now() - timedelta(minutes=5)):
            c.update()

        for c in Component.objects.filter(last_status__isnull=True):
            c.update()

        context.update({
            'status_level': status_level,
            'component_list': Component.objects.all(),
        })
        return context
