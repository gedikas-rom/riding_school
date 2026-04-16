import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta


class RSLessonSlot(Document):

    def validate(self):
        self.validate_participants()
        self.validate_horse()
        self.validate_instructor()
        self.validate_facility()

    def validate_participants(self):
        if not self.participants:
            return

        # Max Teilnehmer prüfen
        max_p = self.max_participants or 1
        if len(self.participants) > max_p:
            frappe.throw(
                _("Zu viele Teilnehmer. Maximum: {0}, aktuell: {1}").format(
                    max_p, len(self.participants)
                )
            )

        # Doppelte Reitschüler prüfen
        riders = [p.rider for p in self.participants if p.rider]
        if len(riders) != len(set(riders)):
            frappe.throw(_("Derselbe Reitschüler kann nicht zweimal eingetragen werden."))

        # Doppelte Pferde prüfen
        horses = [p.horse for p in self.participants if p.horse]
        if len(horses) != len(set(horses)):
            frappe.throw(_("Dasselbe Pferd kann nicht zweimal eingetragen werden."))

    def validate_horse(self):
        # Pferde aus participants validieren
        for p in (self.participants or []):
            if not p.horse:
                continue

            horse = frappe.get_doc("RS Horse", p.horse)

            if getattr(horse, 'status', None) and horse.status != "Active":
                frappe.throw(
                    _("Pferd {0} ist nicht verfügbar (Status: {1})").format(
                        horse.horse_name, horse.status
                    )
                )

            # Doppelbuchung prüfen
            conflicts = frappe.db.sql("""
                SELECT s.name FROM `tabRS Lesson Slot` s
                JOIN `tabRS Slot Participant` sp ON sp.parent = s.name
                WHERE sp.horse = %s
                AND s.slot_date = %s
                AND s.name != %s
                AND s.status != 'Cancelled'
                AND (
                    (s.start_time < %s AND s.end_time > %s)
                    OR (s.start_time < %s AND s.end_time > %s)
                    OR (s.start_time >= %s AND s.end_time <= %s)
                )
            """, (
                p.horse, self.slot_date, self.name or "new",
                self.end_time, self.start_time,
                self.end_time, self.start_time,
                self.start_time, self.end_time
            ), as_dict=True)

            if conflicts:
                frappe.throw(
                    _("Pferd {0} ist zu dieser Zeit bereits in einem anderen Slot eingeplant.").format(
                        horse.horse_name
                    )
                )

    def validate_instructor(self):
        if not self.instructor:
            return

        conflicts = frappe.db.sql("""
            SELECT name FROM `tabRS Lesson Slot`
            WHERE instructor = %s
            AND slot_date = %s
            AND name != %s
            AND status != 'Cancelled'
            AND (
                (start_time < %s AND end_time > %s)
                OR (start_time < %s AND end_time > %s)
                OR (start_time >= %s AND end_time <= %s)
            )
        """, (
            self.instructor, self.slot_date, self.name or "new",
            self.end_time, self.start_time,
            self.end_time, self.start_time,
            self.start_time, self.end_time
        ), as_dict=True)

        if conflicts:
            instructor_name = frappe.db.get_value("RS Instructor", self.instructor, "full_name")
            frappe.throw(
                _("Reitlehrer {0} ist zu dieser Zeit bereits eingeplant.").format(instructor_name)
            )

    def validate_facility(self):
        if not self.facility:
            return

        facility = frappe.get_doc("RS Facility", self.facility)

        overlapping = frappe.db.sql("""
            SELECT COUNT(*) as count FROM `tabRS Lesson Slot`
            WHERE facility = %s
            AND slot_date = %s
            AND name != %s
            AND status != 'Cancelled'
            AND (
                (start_time < %s AND end_time > %s)
                OR (start_time < %s AND end_time > %s)
                OR (start_time >= %s AND end_time <= %s)
            )
        """, (
            self.facility, self.slot_date, self.name or "new",
            self.end_time, self.start_time,
            self.end_time, self.start_time,
            self.start_time, self.end_time
        ))[0][0]

        if overlapping >= (facility.capacity or 1):
            frappe.throw(
                _("Reitplatz {0} ist zu dieser Zeit bereits ausgelastet.").format(
                    facility.facility_name
                )
            )

    @frappe.whitelist()
    def release_slot(self):
        if self.status != "Planned":
            frappe.throw(_("Nur Slots im Status 'Planned' können freigegeben werden."))
        self.status = "Released"
        self.save()
        return "Released"
