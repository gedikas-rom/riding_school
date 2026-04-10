import frappe
from frappe import _
from datetime import datetime, timedelta, date


WEEKDAY_MAP = {
    "Montag": 0,
    "Dienstag": 1,
    "Mittwoch": 2,
    "Donnerstag": 3,
    "Freitag": 4,
    "Samstag": 5,
    "Sonntag": 6
}

CONFIG_WEEKDAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}


@frappe.whitelist()
def generate_slots_for_week(week_start_date):
    """
    Generiert Lesson Slots für eine Woche basierend auf
    Reitlehrer-Verfügbarkeiten und Slot-Konfiguration.
    week_start_date: Datum des Montags der gewünschten Woche (YYYY-MM-DD)
    """
    week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
    
    # Slot-Konfiguration laden
    config = frappe.get_single("RS Slot Config")
    slot_duration = int(config.slot_duration)
    
    # Aktive Wochentage aus Config
    active_weekdays = []
    for day_num, field in CONFIG_WEEKDAY_MAP.items():
        if config.get(field):
            active_weekdays.append(day_num)
    
    if not active_weekdays:
        frappe.throw(_("Keine Wochentage in der Slot-Konfiguration aktiviert."))
    
    # Alle Reitlehrer mit Verfügbarkeiten laden
    instructors = frappe.get_all("RS Instructor", fields=["name", "full_name"])
    
    slots_created = 0
    slots_skipped = 0
    
    for instructor in instructors:
        doc = frappe.get_doc("RS Instructor", instructor.name)
        
        if not doc.availability:
            continue
        
        for avail in doc.availability:
            weekday_num = WEEKDAY_MAP.get(avail.weekday)
            if weekday_num is None:
                continue
            
            # Nur aktive Wochentage
            if weekday_num not in active_weekdays:
                continue
            
            # Datum berechnen
            slot_date = week_start + timedelta(days=weekday_num)
            
            # Slots im Zeitfenster generieren
            from_time = datetime.combine(slot_date, avail.from_time)
            to_time = datetime.combine(slot_date, avail.to_time)
            
            current_time = from_time
            while current_time + timedelta(minutes=slot_duration) <= to_time:
                end_time = current_time + timedelta(minutes=slot_duration)
                
                # Prüfen ob Slot bereits existiert
                existing = frappe.db.exists("RS Lesson Slot", {
                    "slot_date": slot_date,
                    "start_time": current_time.time(),
                    "instructor": instructor.name
                })
                
                if existing:
                    slots_skipped += 1
                else:
                    slot = frappe.get_doc({
                        "doctype": "RS Lesson Slot",
                        "slot_date": slot_date,
                        "start_time": current_time.time(),
                        "end_time": end_time.time(),
                        "instructor": instructor.name,
                        "status": "Open",
                        "slot_type": "Individual"
                    })
                    slot.insert(ignore_permissions=True)
                    slots_created += 1
                
                current_time = end_time
    
    frappe.db.commit()
    
    return {
        "success": True,
        "slots_created": slots_created,
        "slots_skipped": slots_skipped,
        "message": f"{slots_created} Slots erstellt, {slots_skipped} bereits vorhanden."
    }
