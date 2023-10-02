// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Collections", {
  refresh: async function (frm) {
    frm
      .get_field("get_outstanding_fees")
      .$input.addClass("btn-warning")
      .css({ "background-color": "#ffc101" });
    frm
      .get_field("get_advance_fees")
      .$input.addClass("btn-success")
      .css({ "background-color": "#28a745", color: "white" });
    if (frm.doc.docstatus == 1 && frm.doc.is_return == 0) {
      var doc = await frappe.call("education.education.api.get_refund_link", {
        name: frm.doc.name,
      });
      if (doc.message) {
        frm.add_custom_button(__("Make Refund"), async function () {
          frm.doc.is_return = 1;
          frm.doc.refund_against = frm.doc.name;
          frm.copy_doc();
        });
      }
    }
  },

  student: function (frm) {
    if (frm.doc.student) {
    }
  },
  discount_type: function (frm) {
    (frm.doc.percentage = 0), (frm.doc.discount_amount = 0);
    if (frm.doc.discount_type === "") {
      frm.set_value("fee_expense_account", "");
    }
  },

  get_outstanding_fees: function (frm) {
    frappe.call({
      method: "education.education.api.get_outstanding_student_fee",
      args: frm.doc.student
        ? {
            student: frm.doc.student,
          }
        : {
            family_code: frm.doc.family_code,
          },
      callback: function (r) {
        if (r.message) {
          frm.set_value("student_fee_details", "");
          for (let i = 0; i < r.message.length; i++) {
            var row = frappe.model.add_child(frm.doc, "student_fee_details");
            const fee = r.message[i];
            row.fees = fee.name;
            row.student_id = fee.student;
            row.student_name = fee.student_name;
            row.discount_type = fee.discount_type;
            row.discount_amount = fee.discount_amount;
            row.percentage = fee.percentage;
            row.amount_before_discount = fee.amount_before_discount;
            row.due_date = fee.due_date;
            row.grand_total_before_tax = fee.grand_total_before_tax;
            row.total_amount = fee.grand_total;
            row.total_taxes_and_charges = fee.total_taxes_and_charges;
            row.outstanding_amount = fee.outstanding_amount;
            row.allocated_amount = fee.outstanding_amount;
            row.month = fee.posting_date;
          }
        }
        refresh_field("student_fee_details");
      },
    });
  },

  get_advance_fees: function (frm) {
    frappe.call({
      method: "education.education.api.get_advanced_student_fee",
      args: frm.doc.student
        ? {
            student: frm.doc.student,
          }
        : {
            family_code: frm.doc.family_code,
          },
      callback: function (r) {
        if (r.message) {
          frm.set_value("student_fee_details", "");
          for (let i = 0; i < r.message.length; i++) {
            var row = frappe.model.add_child(frm.doc, "student_fee_details");
            const fee = r.message[i];
            row.fees = fee.name;
            row.student_id = fee.student;
            row.student_name = fee.student_name;
            row.discount_type = fee.discount_type;
            row.discount_amount = fee.discount_amount;
            row.percentage = fee.percentage;
            row.amount_before_discount = fee.amount_before_discount;
            row.due_date = fee.due_date;
            row.grand_total_before_tax = fee.grand_total_before_tax;
            row.total_amount = fee.grand_total;
            row.total_taxes_and_charges = fee.total_taxes_and_charges;
            row.outstanding_amount = fee.outstanding_amount;
            row.allocated_amount = fee.outstanding_amount;
            row.month = fee.posting_date;
          }
        }
        refresh_field("student_fee_details");
      },
    });
  },
});
