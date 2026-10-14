document.addEventListener("DOMContentLoaded", () => {
    const deleteDialog = document.querySelector("[data-delete-dialog]");
    if (deleteDialog) {
        const expenseName = deleteDialog.querySelector("[data-delete-expense-name]");
        const cancelButton = deleteDialog.querySelector("[data-delete-cancel]");
        const confirmButton = deleteDialog.querySelector("[data-delete-confirm]");
        let triggerButton = null;

        document.querySelectorAll("[data-delete-trigger]").forEach((button) => {
            button.addEventListener("click", () => {
                triggerButton = button;
                expenseName.textContent = button.dataset.expenseTitle;
                confirmButton.setAttribute("form", button.closest("form").id);
                deleteDialog.showModal();
                cancelButton.focus();
            });
        });

        cancelButton.addEventListener("click", () => deleteDialog.close());
        deleteDialog.addEventListener("click", (event) => {
            if (event.target === deleteDialog) deleteDialog.close();
        });
        deleteDialog.addEventListener("close", () => {
            confirmButton.removeAttribute("form");
            triggerButton?.focus();
            triggerButton = null;
        });
    }

    const calculationDialog = document.querySelector("[data-calculation-dialog]");
    if (calculationDialog) {
        const trigger = document.querySelector("[data-calculation-trigger]");
        const closeButton = calculationDialog.querySelector("[data-calculation-close]");
        trigger.addEventListener("click", () => {
            calculationDialog.showModal();
            closeButton.focus();
        });
        closeButton.addEventListener("click", () => calculationDialog.close());
        calculationDialog.addEventListener("click", (event) => {
            if (event.target === calculationDialog) calculationDialog.close();
        });
        calculationDialog.addEventListener("close", () => trigger.focus());
    }

    const splitMethod = document.querySelector("[data-split-method]");
    const customShares = document.querySelector("[data-custom-shares]");
    if (splitMethod && customShares) {
        const participantInputs = [...document.querySelectorAll('input[name="participants"]')];
        const updateShares = () => {
            const isCustom = splitMethod.querySelector('input[value="custom"]')?.checked;
            customShares.hidden = !isCustom;
            customShares.querySelectorAll("[data-custom-share-row]").forEach((row) => {
                const selected = participantInputs.some((input) =>
                    input.value === row.dataset.memberId && input.checked,
                );
                row.hidden = !selected;
            });
        };
        splitMethod.addEventListener("change", updateShares);
        participantInputs.forEach((input) => input.addEventListener("change", updateShares));
        updateShares();
    }

    const formset = document.querySelector("[data-member-formset]");
    if (!formset) return;

    const list = formset.querySelector("[data-form-list]");
    const template = formset.querySelector("[data-empty-form]");
    const totalInput = document.querySelector("#id_members-TOTAL_FORMS");
    const memberLabel = formset.dataset.memberLabel;
    const removeMemberLabel = formset.dataset.removeMemberLabel;

    const reindexRows = () => {
        const rows = [...list.querySelectorAll("[data-form-row]")];
        rows.forEach((row, index) => {
            row.querySelectorAll("input, label").forEach((element) => {
                if (element.name) {
                    element.name = element.name.replace(/members-\d+-/, `members-${index}-`);
                }
                if (element.id) {
                    element.id = element.id.replace(/members-\d+-/, `members-${index}-`);
                }
                if (element.htmlFor) {
                    element.htmlFor = element.htmlFor.replace(/members-\d+-/, `members-${index}-`);
                }
            });
            const label = row.querySelector("label");
            if (label) label.textContent = `${memberLabel} ${index + 1}`;
            row.querySelector("[data-remove-member]")?.setAttribute(
                "aria-label", `${removeMemberLabel} ${index + 1}`,
            );
        });
        totalInput.value = rows.length;
    };

    formset.addEventListener("click", (event) => {
        const addButton = event.target.closest("[data-add-member]");
        if (addButton) {
            const index = Number(totalInput.value);
            const fragment = template.content.cloneNode(true);
            fragment.querySelectorAll("input, label").forEach((element) => {
                if (element.name) element.name = element.name.replaceAll("__prefix__", index);
                if (element.id) element.id = element.id.replaceAll("__prefix__", index);
                if (element.htmlFor) element.htmlFor = element.htmlFor.replaceAll("__prefix__", index);
            });
            list.append(fragment);
            reindexRows();
            list.lastElementChild.querySelector("input[type='text']")?.focus();
            return;
        }

        const removeButton = event.target.closest("[data-remove-member]");
        if (removeButton) {
            removeButton.closest("[data-form-row]").remove();
            reindexRows();
        }
    });
});

