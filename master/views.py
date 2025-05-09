from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages

def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'master/login.html', {'error': 'Invalid credentials'})
    return render(request, 'master/login.html')

@login_required
def dashboard_view(request):
    return render(request, 'master/dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')
from django.shortcuts import render, redirect
from .forms import ExcelUploadForm
from .models import ExcelUpload, StudentRecord
import pandas as pd
import os
def student_data_view(request):
    upload_form = ExcelUploadForm()
    files = ExcelUpload.objects.order_by('-uploaded_at')
    table_data = []

    # ✅ Handle file upload
    if request.method == 'POST' and 'upload_submit' in request.POST:
        upload_form = ExcelUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            upload_form.save()
            return redirect('student_data_view')

    # ✅ Combine and read all Excel files
    all_files = ExcelUpload.objects.all()
    combined_df = pd.DataFrame()

    for file_obj in all_files:
        try:
            file_path = file_obj.file.path
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext == '.xlsx':
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                continue  # skip unknown types

            combined_df = pd.concat([combined_df, df], ignore_index=True)

        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    # ✅ Drop duplicates within Excel file data
    if not combined_df.empty:
        combined_df.drop_duplicates(subset=['Student ID', 'Student Name'], inplace=True)

        # ✅ Avoid inserting already saved DB records
        existing_records = StudentRecord.objects.values_list('student_id', 'student_name')
        existing_set = set((str(i).strip(), n.strip().lower()) for i, n in existing_records)

        for _, row in combined_df.iterrows():
            student_id = str(row.get('Student ID', '')).strip()
            student_name = str(row.get('Student Name', '')).strip().lower()

            if (student_id, student_name) not in existing_set:
                StudentRecord.objects.create(
                    student_id=student_id,
                    student_name=row.get('Student Name', ''),
                    guardian_name=row.get('Guardian Name', ''),
                    guardian_phone=row.get('Guardian Phone Number', ''),
                    guardian_relation=row.get('Guardian Relation with Student', ''),
                    department=row.get('Department', '')
                )
                existing_set.add((student_id, student_name))  # avoid re-saving in loop

    # ✅ Always show saved records from DB
    saved_records = StudentRecord.objects.all().values(
        'student_id', 'student_name', 'guardian_name',
        'guardian_phone', 'guardian_relation', 'department'
    )
    table_data = list(saved_records)

    return render(request, 'master/student_form.html', {
        'upload_form': upload_form,
        'files': files,
        'table_data': table_data
    })
from .models import SentMessage, StudentRecord
def compose_message(request):
    departments = StudentRecord.objects.values_list('department', flat=True).distinct()
    departments = sorted(set(departments))

    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        send_sms = 'sms' in request.POST
        send_whatsapp = 'whatsapp' in request.POST
        department = request.POST.get('department')

        # ✅ Save to SentMessage model
        SentMessage.objects.create(
            subject=subject,
            message=message,
            send_sms=send_sms,
            send_whatsapp=send_whatsapp,
            department=department
        )

        # (Optional) Send SMS or WhatsApp logic here using Twilio

        return redirect('compose_message')  # reload page or go to message history

    return render(request, 'master/compose_message.html', {
        'departments': departments
    })
from .models import SentMessage

@login_required
def message_history_view(request):
    channel_filter = request.GET.get('channel', '')
    status_filter = request.GET.get('status', '')

    messages = SentMessage.objects.all().order_by('-sent_at')

    # Filter by channel
    if channel_filter == 'sms':
        messages = messages.filter(send_sms=True)
    elif channel_filter == 'whatsapp':
        messages = messages.filter(send_whatsapp=True)

    # (Optional) Filter by status if you are storing delivery status
    if status_filter:
        messages = messages.filter(status=status_filter)  # Only if you add status field

    return render(request, 'master/message_history.html', {
        'messages': messages,
        'channel_filter': channel_filter,
        'status_filter': status_filter,
    })

from django.shortcuts import render
from .models import StudentRecord, SentMessage
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone
 
def dashboard_view(request):
    total_students = StudentRecord.objects.count()
    messages_sent = SentMessage.objects.count()
    active_departments = SentMessage.objects.values('department').distinct().count()
 
    # Delivery Rate (Example: Assume all messages are delivered)
    delivery_rate = 100  # Static or calculate based on real delivery logic
 
    # Weekly Chart Data
    today = timezone.now()
    week_ago = today - timedelta(days=6)
 
    last_7_days = [
        (today - timedelta(days=i)).date()
        for i in range(6, -1, -1)
    ]
 
    message_data = (
        SentMessage.objects
        .filter(sent_at__date__in=last_7_days)
        .values('sent_at__date')
        .annotate(count=Count('id'))
    )
 
    date_count_map = {entry['sent_at__date']: entry['count'] for entry in message_data}
 
    labels = [date.strftime("%Y-%m-%d") for date in last_7_days]
    counts = [date_count_map.get(date, 0) for date in last_7_days]
 
    # Recent Messages (last 5)
    recent_messages = SentMessage.objects.order_by('-sent_at')[:5]
 
    context = {
        'total_students': total_students,
        'messages_sent': messages_sent,
        'active_departments': active_departments,
        'delivery_rate': delivery_rate,
        'labels': labels,
        'counts': counts,
        'recent_messages': recent_messages
    }
 
    return render(request, 'master/dashboard.html', context)