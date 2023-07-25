// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Fee Collections", {
  // after_save: function (frm) {
  //   if (frm.doc.discount_type) {
  //     for (let i = 0; i < frm.doc.student_fee_details.length; i++) {
  //       const e = frm.doc.student_fee_details[i];
  //       if (e.discount_type == "Percentage") {
  //         if (
  //           frm.doc.discount_type != e.discount_type ||
  //           frm.doc.percentage != e.percentage
  //         ) {
  //           frm.trigger("get_student_details");
  //           // frm.save()
  //         }
  //       } else {
  //         if (
  //           frm.doc.discount_type != e.discount_type &&
  //           frm.doc.discount_amount != e.discount_amount
  //         ) {
  //           frm.trigger("get_student_details");
  //         }
  //       }
  //     }
  //   }
  // },

  get_student_details: function (frm) {
    frm.set_value("student_fee_details", "");
    if (frm.doc.student) {
      frappe.call({
        method: "education.education.api.get_student_fee_details",
        args: {
          student: frm.doc.student,
        },
        callback: function (r) {
          if (r.message) {
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
            }
          }
          refresh_field("student_fee_details");
        },
      });
    }
    if (frm.doc.family_code) {
      frappe.call({
        method: "education.education.api.get_student_fee_details",
        args: {
          family_code: frm.doc.family_code,
        },
        callback: function (r) {
          if (r.message) {
            for (let i = 0; i < r.message.length; i++) {
              var row = frappe.model.add_child(frm.doc, "student_fee_details");
              const fee = r.message[i];
              row.fees = fee.name;
              row.student_id = fee.student;
              row.student_name = fee.student_name;
              row.discount_type = fee.discount_type;
              row.discount_amount = fee.discount_amount;
              row.percentage = fee.percentage;
              row.due_date = fee.due_date;
              row.grand_total_before_tax = fee.grand_total_before_tax;
              row.total_amount = fee.grand_total;
              row.total_taxes_and_charges = fee.total_taxes_and_charges;
              row.outstanding_amount = fee.outstanding_amount;
              row.allocated_amount = fee.outstanding_amount;
            }
          }
          refresh_field("student_fee_details");
        },
      });
    }
  },
});
