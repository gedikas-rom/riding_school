import frappe
from frappe.model.document import Document

class RSInstructor(Document):
    def validate(self):
        self.prevent_duplicate_qualifications()
        self.update_qualification_summary()

    def prevent_duplicate_qualifications(self):
        seen = []
        for row in self.qualifications:
            if row.qualification in seen:
                frappe.throw(f"Qualifikation <b>{row.qualification}</b> wurde mehrfach eingetragen.")
            seen.append(row.qualification)

    def update_qualification_summary(self):
        quals = [row.qualification for row in self.qualifications if row.qualification]
        self.qualification_summary = ", ".join(quals)
