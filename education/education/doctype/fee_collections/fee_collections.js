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
      .$input.addClass("btn-primary")
      .css({ "background-color": "#2490ef", color: "white" });
    if (frm.doc.docstatus == 1 && frm.doc.is_return == 0) {
      // var doc = await frappe.call("education.education.api.get_refund_link", {
      //   name: frm.doc.name,
      // });
      // if (doc.message) {
      frm.add_custom_button(__("Make Refund"), async function () {
        const array = [];
        frm.doc.refund_against = frm.doc.name;
        // frm.set_value("student_fee_details", ""); // Clear existing details

        // Define a function to make an asynchronous call and return a Promise
        function getFeeDetails(e) {
          return new Promise((resolve, reject) => {
            frappe.call({
              method: "frappe.client.get",
              args: {
                doctype: "Fees",
                name: e.fees,
              },
              callback(r) {
                if (r.message && r.message.is_return === 0) {
                  const fee = r.message;
                  const row = {
                    fees: fee.name,
                    student_id: fee.student,
                    student_name: fee.student_name,
                    discount_type: fee.discount_type,
                    discount_amount: fee.discount_amount,
                    percentage: fee.percentage,
                    amount_before_discount: fee.amount_before_discount,
                    due_date: fee.due_date,
                    grand_total_before_tax: fee.grand_total_before_tax,
                    total_amount: fee.grand_total,
                    total_taxes_and_charges: fee.total_taxes_and_charges,
                    outstanding_amount: e.outstanding_amount,
                    allocated_amount: e.outstanding_amount,
                    month: fee.posting_date,
                  };
                  array.push(row);
                }
                resolve(); // Resolve the Promise when the callback is done
              },
            });
          });
        }

        // Use Promise.all to wait for all asynchronous calls to finish
        const promises = [];
        frm.doc.is_return = 1;
        frm.copy_doc();

        for (let i = 0; i < frm.doc.student_fee_details.length; i++) {
          promises.push(getFeeDetails(frm.doc.student_fee_details[i]));
        }

        // Wait for all promises to complete
        await Promise.all(promises);

        frm.set_value("student_fee_details", array);

        if (frm.doc.student_fee_details.length === 0) {
          frappe.throw(__("All Fees have already been refunded"));
        }
      });
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
            row.is_return = fee.is_return;
          }
        }
        refresh_field("student_fee_details");
      },
    });
    frm.trigger("student_fee_details");
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
    frm.trigger("student_fee_details");
  },

  student_fee_details: function (frm) {
    console.log("cge");
    if (frm.doc.student_fee_details) {
      console.log("in looop");
      let grand_total = 0;
      let grand_total_b_tax = 0;
      let total_tax_a = 0;
      let grand_total_b_d = 0;
      for (let i = 0; i < frm.doc.student_fee_details.length; i++) {
        const e = frm.doc.student_fee_details[i];
        grand_total += e.grand_total;
        grand_total_b_tax += e.grand_total_before_tax;
        total_tax_a += e.total_taxes_and_charges;
        grand_total_b_d += e.amount_before_discount;
      }
      frm.set_value("grand_total", grand_total);
      frm.set_value("grand_total_b_tax", grand_total_b_tax);
      frm.set_value("total_tax_a", total_tax_a);
      frm.set_value("grand_total_b_d", grand_total_b_d);
    }
  },
});
