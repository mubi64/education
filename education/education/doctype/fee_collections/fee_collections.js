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
    frm
      .get_field("get_all_fees")
      .$input.addClass("btn-succsess")
      .css({ "background-color": "#2f9d5f", color: "white" });
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
      callback: async function (r) {
        if (r.message.length == 0) {
          frappe.throw(__("There are no outstanding fee found in the system"));
        }

        processFees(frm, r.message);
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
        processFees(frm, r.message);
      },
    });
  },

  get_all_fees: function (frm) {
    frappe.call({
      method: "education.education.api.get_student_fee_details",
      args: frm.doc.student
        ? {
            student: frm.doc.student,
          }
        : {
            family_code: frm.doc.family_code,
          },
      callback: function (r) {
        processFees(frm, r.message);
      },
    });
  },

  student_fee_details: function (frm) {
    let grand_total = 0;
    let grand_total_b_tax = 0;
    let total_tax_a = 0;
    let grand_total_b_d = 0;
    for (let i = 0; i < frm.doc.student_fee_details.length; i++) {
      const e = frm.doc.student_fee_details[i];
      grand_total += e.total_amount;
      grand_total_b_tax += e.grand_total_before_tax;
      total_tax_a += e.total_taxes_and_charges;
      grand_total_b_d += e.amount_before_discount;
    }
    frm.set_value("grand_total", grand_total);
    frm.set_value("grand_total_b_tax", grand_total_b_tax);
    frm.set_value("total_tax_a", total_tax_a);
    frm.set_value("grand_total_b_d", grand_total_b_d);
  },
});

async function processFees(frm, array) {
  if (array) {
    frm.set_value("student_fee_details", "");
    for (let i = 0; i < array.length; i++) {
      var row = frappe.model.add_child(frm.doc, "student_fee_details");
      const fee = array[i];
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
      try {
        const response = await frappe.call({
          method: "education.education.api.get_fee_doc",
          args: {
            name: fee.name,
          },
        });

        if (response.message && response.message.components) {
          const compoArray = [];
          frm.doc.net_total = 0;
          frm.doc.discount = 0;
          frm.doc.net_total_a_d = 0;
          for (let i = 0; i < response.message.components.length; i++) {
            const ele = response.message.components[i];
            compoArray.push(ele.fees_category);
            let dis_amount = ele.gross_amount - ele.amount;
            frm.doc.net_total += ele.gross_amount;
            frm.doc.discount += dis_amount;
            frm.doc.net_total_a_d += ele.amount;
          }
          // const compoArray = response.message.components.map(
          //   (ele) => ele.fees_category
          // );
          row.components = compoArray.join(", ");
        }
      } catch (error) {
        console.error("Error fetching fee details:", error);
        // Handle the error gracefully (e.g., log it, set a default value, etc.)
      }
    }
  }
  frm.refresh_field("net_total");
  frm.refresh_field("discount");
  frm.refresh_field("net_total_a_d");
  refresh_field("student_fee_details");
  frm.trigger("student_fee_details");
}
