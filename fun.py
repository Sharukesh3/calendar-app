from __future__ import print_function
import datetime
import os
import fitz  # PyMuPDF
import re
from datetime import timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def extract_text_from_pdf(pdf_path):
    document = fitz.open(pdf_path)
    text = ""
    for page_num in range(document.page_count):
        page = document[page_num]
        text += page.get_text()
    return text

def parse_class_timetable(text):
    class_pattern = re.compile(r'(\b(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY)\b)(.*?)(?=\b(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|$)\b)', re.S)
    time_pattern = re.compile(r'(\d{2}:\d{2} (?:am|pm))')
    events = []

    days_map = {
        'MONDAY': '2024-06-24',
        'TUESDAY': '2024-06-25',
        'WEDNESDAY': '2024-06-26',
        'THURSDAY': '2024-06-27',
        'FRIDAY': '2024-06-28'
    }

    matches = class_pattern.findall(text)
    for day, classes in matches:
        day_date = datetime.datetime.strptime(days_map[day], '%Y-%m-%d')
        time_matches = time_pattern.findall(classes)
        subjects = re.findall(r'([A-Z0-9]+.*?)\n', classes)

        if len(time_matches) != len(subjects):
            print(f"Warning: Mismatch in times and subjects for {day}.")
            print(f"Times found: {time_matches}")
            print(f"Subjects found: {subjects}")
            continue

        for i, subject in enumerate(subjects):
            try:
                start_time = datetime.datetime.strptime(time_matches[i], '%I:%M %p').time()
                end_time = (datetime.datetime.combine(day_date, start_time) + timedelta(minutes=50)).time()
                start_datetime = datetime.datetime.combine(day_date, start_time)
                end_datetime = datetime.datetime.combine(day_date, end_time)

                events.append({
                    'summary': subject.strip(),
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'Asia/Kolkata',
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'Asia/Kolkata',
                    },
                })
            except IndexError as e:
                print(f"Error processing subject {subject} on {day}: {e}")
    return events

def create_calendar_events(events):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(r'json/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    for event in events:
        service.events().insert(calendarId='primary', body=event).execute()

def main():
    academic_calendar_text = extract_text_from_pdf(r"pdfs/AY-Calendar-2024-2025-Odd-Semester.pdf")
    timetable_text = extract_text_from_pdf(r"pdfs/class timetable.pdf")
    
    class_events = parse_class_timetable(timetable_text)
    create_calendar_events(class_events)

if __name__ == '__main__':
    main()
