"""
Экспорт данных дашбордов в PDF и Excel.
"""

import logging
from datetime import datetime, timedelta
from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required, permission_required

from visitors.models import Visit, AuditLog, SecurityIncident

logger = logging.getLogger(__name__)


# ==================== HELPER FUNCTIONS ====================

def get_auto_checkin_data(days=7):
    """
    Получение данных для Auto Check-in Dashboard.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Автоматические check-in/out за период (используем AuditLog)
    auto_checkins = AuditLog.objects.filter(
        model='Visit',
        action=AuditLog.ACTION_UPDATE,
        user_agent='HikCentral FaceID System',
        created_at__gte=start_date,
        created_at__lte=end_date,
        changes__reason='Auto check-in via FaceID turnstile'
    ).order_by('-created_at')
    
    auto_checkouts = AuditLog.objects.filter(
        model='Visit',
        action=AuditLog.ACTION_UPDATE,
        user_agent='HikCentral FaceID System',
        created_at__gte=start_date,
        created_at__lte=end_date,
        changes__reason='Auto checkout via FaceID turnstile'
    ).order_by('-created_at')
    
    # Статистика
    total_auto_checkins = auto_checkins.count()
    total_auto_checkouts = auto_checkouts.count()
    
    # Аномалии
    incidents = SecurityIncident.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    ).select_related('visit__guest', 'visit__employee').order_by('-detected_at')
    
    return {
        'auto_checkins': auto_checkins[:100],  # Последние 100
        'auto_checkouts': auto_checkouts[:100],
        'total_auto_checkins': total_auto_checkins,
        'total_auto_checkouts': total_auto_checkouts,
        'incidents': incidents[:50],  # Последние 50
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
    }


def get_security_incidents_data(days=30, status=None, incident_type=None, severity=None):
    """
    Получение данных для Security Incidents Dashboard.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Базовый queryset
    incidents = SecurityIncident.objects.select_related(
        'visit__guest', 'visit__employee', 'visit__department', 'assigned_to'
    ).filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    )
    
    # Фильтры
    if status:
        incidents = incidents.filter(status=status)
    if incident_type:
        incidents = incidents.filter(incident_type=incident_type)
    if severity:
        incidents = incidents.filter(severity=severity)
    
    incidents = incidents.order_by('-detected_at')
    
    # Статистика
    stats = {
        'total': incidents.count(),
        'by_severity': incidents.values('severity').annotate(count=Count('id')),
        'by_type': incidents.values('incident_type').annotate(count=Count('id')),
        'by_status': incidents.values('status').annotate(count=Count('id')),
    }
    
    return {
        'incidents': incidents,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
    }


def get_hikcentral_data():
    """
    Получение данных для HikCentral Dashboard.
    """
    from hikvision_integration.services import HikCentralServer
    from django.conf import settings
    
    try:
        hc_server = HikCentralServer.objects.first()
        
        if not hc_server:
            return {'error': 'HikCentral server not configured'}
        
        # Статистика за последние 24 часа
        last_24h = timezone.now() - timedelta(hours=24)
        
        # Статистика за последние 24 часа (упрощенная версия)
        stats = {
            'server_name': hc_server.name,
            'server_url': hc_server.base_url,
            'is_active': hc_server.is_active,
            'faces_enrolled_24h': Visit.objects.filter(
                hikcentral_person_id__isnull=False,
                registered_at__gte=last_24h
            ).count(),
            'access_granted_24h': Visit.objects.filter(
                access_granted=True,
                registered_at__gte=last_24h
            ).count(),
            'auto_actions_24h': AuditLog.objects.filter(
                model='Visit',
                action=AuditLog.ACTION_UPDATE,
                user_agent='HikCentral FaceID System',
                created_at__gte=last_24h
            ).count(),
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting HikCentral data: {e}", exc_info=True)
        return {'error': str(e)}


# ==================== PDF EXPORT VIEWS ====================

@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def export_auto_checkin_pdf(request):
    """
    Экспорт Auto Check-in Dashboard в PDF.
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        days = int(request.GET.get('days', 7))
        data = get_auto_checkin_data(days=days)
        
        # Обрабатываем AuditLog данные для PDF
        processed_checkins = []
        for log in data['auto_checkins']:
            try:
                visit = Visit.objects.select_related('guest', 'employee', 'department').get(id=log.object_id)
                processed_checkins.append([
                    log.created_at.strftime('%d.%m.%Y %H:%M'),
                    visit.guest.full_name if visit.guest else '-',
                    visit.employee.get_full_name() if visit.employee else '-',
                    visit.department.name if visit.department else '-',
                ])
            except Visit.DoesNotExist:
                pass
        
        processed_checkouts = []
        for log in data['auto_checkouts']:
            try:
                visit = Visit.objects.select_related('guest', 'employee', 'department').get(id=log.object_id)
                processed_checkouts.append([
                    log.created_at.strftime('%d.%m.%Y %H:%M'),
                    visit.guest.full_name if visit.guest else '-',
                    visit.employee.get_full_name() if visit.employee else '-',
                    visit.department.name if visit.department else '-',
                ])
            except Visit.DoesNotExist:
                pass
        
        # Создаем PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Заголовок
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # CENTER
        )
        story.append(Paragraph('📊 Auto Check-in Dashboard Report', title_style))
        
        # Метаданные
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            alignment=1,  # CENTER
        )
        meta_text = f"""
        <b>Период:</b> {data['start_date'].strftime('%d.%m.%Y %H:%M')} - {data['end_date'].strftime('%d.%m.%Y %H:%M')} ({data['days']} дней)<br/>
        <b>Сгенерировано:</b> {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}<br/>
        <b>Сотрудник:</b> {request.user.get_full_name() or request.user.username}
        """
        story.append(Paragraph(meta_text, meta_style))
        
        # Статистика
        stats_data = [
            ['Метрика', 'Значение'],
            ['Автоматических входов', str(data['total_auto_checkins'])],
            ['Автоматических выходов', str(data['total_auto_checkouts'])],
            ['Аномалий обнаружено', str(len(data['incidents']))],
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph('<b>📈 Статистика</b>', styles['Heading2']))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Таблица Check-ins
        if processed_checkins:
            story.append(Paragraph('<b>✅ Автоматические Check-ins</b>', styles['Heading2']))
            checkins_data = [['Дата/Время', 'Гость', 'Принимающий', 'Департамент']] + processed_checkins[:50]
            
            checkins_table = Table(checkins_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch])
            checkins_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(checkins_table)
            story.append(Spacer(1, 20))
        
        # Таблица Check-outs
        if processed_checkouts:
            story.append(Paragraph('<b>🚪 Автоматические Check-outs</b>', styles['Heading2']))
            checkouts_data = [['Дата/Время', 'Гость', 'Принимающий', 'Департамент']] + processed_checkouts[:50]
            
            checkouts_table = Table(checkouts_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch])
            checkouts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(checkouts_table)
        
        # Генерируем PDF
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        
        # Отправляем response
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'auto_checkin_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Auto Check-in PDF exported by {request.user.username}")
        return response
        
    except ImportError:
        logger.error("ReportLab not installed")
        return HttpResponse(
            "ReportLab не установлен. Запустите: poetry run pip install reportlab",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting Auto Check-in PDF: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте PDF: {e}", status=500)


@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def export_security_incidents_pdf(request):
    """
    Экспорт Security Incidents Dashboard в PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        days = int(request.GET.get('days', 30))
        status = request.GET.get('status')
        incident_type = request.GET.get('incident_type')
        severity = request.GET.get('severity')
        
        data = get_security_incidents_data(
            days=days,
            status=status,
            incident_type=incident_type,
            severity=severity
        )
        
        # Создаем PDF (landscape для широких таблиц)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        story = []
        
        # Заголовок
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # CENTER
        )
        story.append(Paragraph('🚨 Security Incidents Report', title_style))
        
        # Метаданные
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            alignment=1,  # CENTER
        )
        meta_text = f"""
        <b>Период:</b> {data['start_date'].strftime('%d.%m.%Y %H:%M')} - {data['end_date'].strftime('%d.%m.%Y %H:%M')} ({data['days']} дней)<br/>
        <b>Сгенерировано:</b> {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}<br/>
        <b>Сотрудник:</b> {request.user.get_full_name() or request.user.username}
        """
        story.append(Paragraph(meta_text, meta_style))
        
        # Статистика
        stats_data = [
            ['Метрика', 'Значение'],
            ['Всего инцидентов', str(data['stats']['total'])],
        ]
        
        for stat in data['stats']['by_severity']:
            stats_data.append([f"Уровень {stat['severity'].upper()}", str(stat['count'])])
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.red),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph('<b>📊 Общая статистика</b>', styles['Heading2']))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Таблица инцидентов
        if data['incidents']:
            story.append(Paragraph('<b>📋 Детальный список инцидентов</b>', styles['Heading2']))
            
            incidents_data = [['Дата', 'Тип', 'Уровень', 'Статус', 'Гость', 'Принимающий', 'Описание']]
            
            for incident in data['incidents'][:100]:  # Ограничиваем 100 записями
                incidents_data.append([
                    incident.detected_at.strftime('%d.%m.%y %H:%M'),
                    incident.get_incident_type_display(),
                    incident.get_severity_display(),
                    incident.get_status_display(),
                    incident.visit.guest.full_name if incident.visit and incident.visit.guest else '-',
                    incident.visit.employee.get_full_name() if incident.visit and incident.visit.employee else '-',
                    incident.description[:50] + '...' if len(incident.description) > 50 else incident.description,
                ])
            
            incidents_table = Table(incidents_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1*inch, 1.5*inch, 1.5*inch, 2.5*inch])
            incidents_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(incidents_table)
        
        # Генерируем PDF
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        
        # Отправляем response
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'security_incidents_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Security Incidents PDF exported by {request.user.username}")
        return response
        
    except ImportError:
        return HttpResponse(
            "ReportLab не установлен. Запустите: poetry run pip install reportlab",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting Security Incidents PDF: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте PDF: {e}", status=500)


@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def export_hikcentral_pdf(request):
    """
    Экспорт HikCentral Dashboard в PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        data = get_hikcentral_data()
        
        # Создаем PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Заголовок
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # CENTER
        )
        story.append(Paragraph('🔌 HikCentral Status Report', title_style))
        
        # Метаданные
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            alignment=1,  # CENTER
        )
        meta_text = f"""
        <b>Сгенерировано:</b> {timezone.now().strftime('%d.%m.%Y %H:%M:%S')}<br/>
        <b>Сотрудник:</b> {request.user.get_full_name() or request.user.username}
        """
        story.append(Paragraph(meta_text, meta_style))
        
        if 'error' in data:
            # Ошибка
            error_style = ParagraphStyle(
                'Error',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20,
                alignment=1,  # CENTER
                textColor=colors.red,
            )
            story.append(Paragraph(f'⚠️ Ошибка: {data["error"]}', error_style))
        else:
            # Информация о сервере
            story.append(Paragraph('<b>🖥️ Информация о сервере</b>', styles['Heading2']))
            
            server_data = [
                ['Параметр', 'Значение'],
                ['Имя сервера', data.get('server_name', '-')],
                ['URL', data.get('server_url', '-')],
                ['Статус', 'Активен' if data.get('is_active') else 'Неактивен'],
            ]
            
            server_table = Table(server_data, colWidths=[3*inch, 3*inch])
            server_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(server_table)
            story.append(Spacer(1, 20))
            
            # Активность за 24 часа
            story.append(Paragraph('<b>📊 Активность за последние 24 часа</b>', styles['Heading2']))
            
            activity_data = [
                ['Метрика', 'Значение'],
                ['Лиц зарегистрировано', str(data.get('faces_enrolled_24h', 0))],
                ['Доступов выдано', str(data.get('access_granted_24h', 0))],
                ['Автоматических действий', str(data.get('auto_actions_24h', 0))],
            ]
            
            activity_table = Table(activity_data, colWidths=[3*inch, 2*inch])
            activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(activity_table)
            story.append(Spacer(1, 20))
            
            # Информационный блок
            info_style = ParagraphStyle(
                'Info',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=20,
                leftIndent=20,
                rightIndent=20,
                borderColor=colors.lightblue,
                borderWidth=1,
                borderPadding=10,
            )
            info_text = """
            <b>ℹ️ Информация:</b><br/>
            Данный отчет показывает текущий статус интеграции с HikCentral Professional.<br/>
            Статистика включает только действия за последние 24 часа.<br/>
            Для полной диагностики используйте веб-интерфейс HikCentral Dashboard.
            """
            story.append(Paragraph(info_text, info_style))
        
        # Генерируем PDF
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        
        # Отправляем response
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'hikcentral_status_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"HikCentral PDF exported by {request.user.username}")
        return response
        
    except ImportError:
        return HttpResponse(
            "ReportLab не установлен. Запустите: poetry run pip install reportlab",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting HikCentral PDF: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте PDF: {e}", status=500)


# ==================== EXCEL EXPORT VIEWS ====================

@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def export_auto_checkin_excel(request):
    """
    Экспорт Auto Check-in Dashboard в Excel.
    """
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        
        days = int(request.GET.get('days', 7))
        data = get_auto_checkin_data(days=days)
        
        # Создаем Excel workbook
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Auto Check-ins
            checkins_data = []
            for log in data['auto_checkins']:
                # Получаем Visit объект по object_id
                try:
                    visit = Visit.objects.select_related('guest', 'employee', 'department').get(id=log.object_id)
                    checkins_data.append({
                        'Дата/Время': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Гость': visit.guest.full_name if visit.guest else '-',
                        'Принимающий': visit.employee.get_full_name() if visit.employee else '-',
                        'Департамент': visit.department.name if visit.department else '-',
                        'Событие': 'Вход',
                    })
                except Visit.DoesNotExist:
                    pass
            
            if checkins_data:
                df_checkins = pd.DataFrame(checkins_data)
                df_checkins.to_excel(writer, sheet_name='Check-ins', index=False)
            
            # Sheet 2: Auto Check-outs
            checkouts_data = []
            for log in data['auto_checkouts']:
                # Получаем Visit объект по object_id
                try:
                    visit = Visit.objects.select_related('guest', 'employee', 'department').get(id=log.object_id)
                    checkouts_data.append({
                        'Дата/Время': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Гость': visit.guest.full_name if visit.guest else '-',
                        'Принимающий': visit.employee.get_full_name() if visit.employee else '-',
                        'Департамент': visit.department.name if visit.department else '-',
                        'Событие': 'Выход',
                    })
                except Visit.DoesNotExist:
                    pass
            
            if checkouts_data:
                df_checkouts = pd.DataFrame(checkouts_data)
                df_checkouts.to_excel(writer, sheet_name='Check-outs', index=False)
            
            # Sheet 3: Security Incidents
            incidents_data = []
            for incident in data['incidents']:
                incidents_data.append({
                    'Дата обнаружения': incident.detected_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'Тип': incident.get_incident_type_display(),
                    'Уровень': incident.get_severity_display(),
                    'Статус': incident.get_status_display(),
                    'Гость': incident.visit.guest.full_name if incident.visit and incident.visit.guest else '-',
                    'Описание': incident.description,
                })
            
            if incidents_data:
                df_incidents = pd.DataFrame(incidents_data)
                df_incidents.to_excel(writer, sheet_name='Incidents', index=False)
        
        output.seek(0)
        
        # Отправляем response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'auto_checkin_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Auto Check-in Excel exported by {request.user.username}")
        return response
        
    except ImportError as e:
        logger.error(f"Required library not installed: {e}")
        return HttpResponse(
            f"Необходимая библиотека не установлена: {e}. Запустите: poetry run pip install pandas openpyxl",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting Auto Check-in Excel: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте Excel: {e}", status=500)


@login_required
@permission_required('visitors.view_securityincident', raise_exception=True)
def export_security_incidents_excel(request):
    """
    Экспорт Security Incidents Dashboard в Excel.
    """
    try:
        import pandas as pd
        
        days = int(request.GET.get('days', 30))
        status = request.GET.get('status')
        incident_type = request.GET.get('incident_type')
        severity = request.GET.get('severity')
        
        data = get_security_incidents_data(
            days=days,
            status=status,
            incident_type=incident_type,
            severity=severity
        )
        
        # Создаем DataFrame
        incidents_data = []
        for incident in data['incidents']:
            incidents_data.append({
                'ID': incident.id,
                'Дата обнаружения': incident.detected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Тип инцидента': incident.get_incident_type_display(),
                'Уровень важности': incident.get_severity_display(),
                'Статус': incident.get_status_display(),
                'Гость': incident.visit.guest.full_name if incident.visit and incident.visit.guest else '-',
                'Принимающий': incident.visit.employee.get_full_name() if incident.visit and incident.visit.employee else '-',
                'Департамент': incident.visit.department.name if incident.visit and incident.visit.department else '-',
                'Описание': incident.description,
                'Назначен': incident.assigned_to.get_full_name() if incident.assigned_to else '-',
                'Дата решения': incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if incident.resolved_at else '-',
                'Заметки': incident.resolution_notes or '-',
            })
        
        df = pd.DataFrame(incidents_data)
        
        # Создаем Excel файл
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Security Incidents', index=False)
        
        output.seek(0)
        
        # Отправляем response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'security_incidents_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Security Incidents Excel exported by {request.user.username}")
        return response
        
    except ImportError as e:
        return HttpResponse(
            f"Необходимая библиотека не установлена: {e}. Запустите: poetry run pip install pandas openpyxl",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting Security Incidents Excel: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте Excel: {e}", status=500)


@login_required
@permission_required('visitors.view_visit', raise_exception=True)
def export_hikcentral_excel(request):
    """
    Экспорт HikCentral Dashboard в Excel.
    """
    try:
        import pandas as pd
        
        data = get_hikcentral_data()
        
        if 'error' in data:
            return HttpResponse(f"Ошибка: {data['error']}", status=500)
        
        # Создаем DataFrame со статистикой
        stats_data = [
            {'Метрика': 'Сервер', 'Значение': data.get('server_name', '-')},
            {'Метрика': 'URL', 'Значение': data.get('server_url', '-')},
            {'Метрика': 'Статус', 'Значение': 'Активен' if data.get('is_active') else 'Неактивен'},
            {'Метрика': 'Лица зарегистрированы (24ч)', 'Значение': data.get('faces_enrolled_24h', 0)},
            {'Метрика': 'Доступ выдан (24ч)', 'Значение': data.get('access_granted_24h', 0)},
            {'Метрика': 'Автоматические действия (24ч)', 'Значение': data.get('auto_actions_24h', 0)},
        ]
        
        df = pd.DataFrame(stats_data)
        
        # Создаем Excel файл
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='HikCentral Status', index=False)
        
        output.seek(0)
        
        # Отправляем response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'hikcentral_status_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"HikCentral Excel exported by {request.user.username}")
        return response
        
    except ImportError as e:
        return HttpResponse(
            f"Необходимая библиотека не установлена: {e}. Запустите: poetry run pip install pandas openpyxl",
            status=500
        )
    except Exception as e:
        logger.error(f"Error exporting HikCentral Excel: {e}", exc_info=True)
        return HttpResponse(f"Ошибка при экспорте Excel: {e}", status=500)

