import frappe
from frappe.model.document import Document

class RSTimeCard(Document):
    def before_save(self):
        self.remaining_lessons = (self.total_lessons or 0) - (self.used_lessons or 0)
        if self.remaining_lessons <= 0:
            self.status = "Exhausted"
