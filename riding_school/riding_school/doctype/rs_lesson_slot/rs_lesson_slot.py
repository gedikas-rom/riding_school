import frappe
from frappe.model.document import Document

class RSLessonSlot(Document):
    pass


    @frappe.whitelist()
    def release_slot(self):
        if self.status != "Planned":
            frappe.throw(_("Nur Slots im Status 'Planned' können freigegeben werden."))
        if not self.horse:
            frappe.throw(_("Bitte zuerst ein Pferd zuweisen."))
        if not self.facility:
            frappe.throw(_("Bitte zuerst einen Reitplatz zuweisen."))
        self.status = "Released"
        self.save()
        return "Released"
