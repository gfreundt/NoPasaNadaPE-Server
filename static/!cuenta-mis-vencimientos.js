function calculateDays(dateInputId, outputSpanId) {
    const dateInput = document.getElementById(dateInputId);
    const outputSpan = document.getElementById(outputSpanId);
    if (!dateInput.value) {
        outputSpan.textContent = "";
        return;
    }
    const today = new Date();
    const futureDate = new Date(dateInput.value);
    const timeDiff = futureDate.getTime() - today.getTime();
    const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
    if (daysDiff < 0) {
        outputSpan.innerHTML = "<span class='text-danger fw-bold'>Vencido</span>";
    } else {
        outputSpan.innerHTML = `<span class='text-success fw-bold'>${daysDiff.toLocaleString()} días</span>`;
    }
}

let passportCount = 0;
const maxPassports = 3;
const addButton = document.getElementById('add-passport-btn');

document.addEventListener("DOMContentLoaded", () => {
    // DNI
    calculateDays('dniDate', 'dniDays');

    // Auto Data
    document.querySelectorAll("[id^=autoDate]").forEach(input => {
        const num = input.id.replace("autoDate", "");
        calculateDays(input.id, "autoDays" + num);
    });
});



function addPassportSection(country = "", date = "") {
    if (passportCount >= maxPassports) return;
    passportCount++;

    const container = document.getElementById('passport-container');
    const newSection = document.createElement('div');
    newSection.className = 'passport-entry mb-2 border rounded p-2 bg-light';
    newSection.innerHTML = `
    <button type="button" class="btn btn-sm btn-danger float-end mb-1 rounded-circle" onclick="removePassportSection(this)">
        <i class="bi bi-trash-fill"></i>
    </button>
    <div class="form-group mb-1">
        <label for="passportCountry${passportCount}" class="form-label small mb-1">País de Emisión</label>
        <select class="form-select form-select-sm" id="passportCountry${passportCount}" name="passportCountry${passportCount}" data-original="${country}">
            ${getCountryOptions(country)}
        </select>
    </div>
    <div class="form-group mb-1">
        <label for="passportDate${passportCount}" class="form-label small mb-1">Fecha de Vencimiento</label>
        <input type="date" class="form-control form-control-sm" id="passportDate${passportCount}" name="passportDate${passportCount}" value="${date}" data-original="${date}"
        onchange="calculateDays('passportDate${passportCount}', 'passportDays${passportCount}')">
    </div>
    <p class="mt-2 mb-1 small">Vigencia <span class="fw-bold" id="passportDays${passportCount}"></span></p>
    `;
    container.insertBefore(newSection, addButton);

    if (passportCount >= maxPassports) addButton.style.display = 'none';

    // Trigger calculation if prefilled date exists
    if (date) {
        calculateDays(`passportDate${passportCount}`, `passportDays${passportCount}`);
    }
}

function removePassportSection(button) {
    const sectionToRemove = button.closest('.passport-entry');
    if (sectionToRemove) {
        sectionToRemove.remove();
        passportCount--;
        if (passportCount < maxPassports) addButton.style.display = 'block';
    }
}

function getCountryOptions(selected = "") {
    const countries = [
        "Argentina", "Bolivia", "Brasil", "Chile", "Colombia", "Costa Rica", 
        "Ecuador", "México", "Estados Unidos", "Canadá", "España", "Italia",
        "Francia", "Alemania", "Reino Unido", "Japón", "Otros"
    ];

    // sorted alphabetically (case-insensitive)
    countries.sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));

    return countries.map(c => 
        `<option value="${c}" ${c === selected ? "selected" : ""}>${c}</option>`
    ).join("");
}


