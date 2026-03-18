// listens for click of Limpiar and wipes text in activities text area
document.addEventListener('DOMContentLoaded', function () {
    const clearButton = document.getElementById('clear-btn');
    const textarea = document.getElementById('activities-text-area');

    if (clearButton && textarea) {
        clearButton.addEventListener('click', function () {
            textarea.value = "";
        });
    }
});

/**
 * Updates a single element with new innerHTML content.
 * @param {string} id - The ID of the HTML element to update.
 * @param {string} content - The new content to set.
 */
function updateElementContent(id, content) {
    const element = document.getElementById(id);
    if (element) {
        element.innerHTML = '';
        const div = document.createElement('div');
        div.innerHTML = content;
        element.appendChild(div);
    }
}

/**
 * Updates the new Scrape Data table using an array of categories and columns.
 * Assumes the data structure is: data.scrape_data[category][column].
 * @param {object} data - The entire JSON data object fetched from the server.
 */
function updateScrapeData(data) {
    // Definimos las categorías y las columnas según el HTML
    const categories = [
                    "DataMtcRecordsConductores",
                    "DataMtcBrevetes",
                    "DataSatMultas",
                    "DataMtcRevisionesTecnicas",
                    "DataSutranMultas",
                    "DataSunarpFichas",
                    "DataApesegSoats",
                    "DataSatImpuestosCodigos",
                    "DataCallaoMultas"];
    const columns = ['status', 'pendientes', 'eta', 'threads_activos','alertas','boletines'];

    if (data.scrapers_kpis) {
        categories.forEach(category => {
            if (data.scrapers_kpis[category]) {
                columns.forEach(column => {
                    // Construye el ID en formato: scrape-columna-categoria
                    const id = `scraperkpi-${column}-${category}`;
                    const content = data.scrapers_kpis[category][column];
                    
                    // Aseguramos que el contenido exista antes de intentar actualizar
                    if (content !== undefined) {
                        updateElementContent(id, content);
                    }
                });
            }
        });
    }
}


// updates dashboard regularly
function updateDashboard() {
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            
            const iconMap = {
                3: "bi-check-circle-fill text-success",
                0: "bi-hourglass-split text-secondary",
                2: "bi-x-circle-fill text-danger",
                1: "bi-caret-right-square text-success"
            };

            // Update cards (0-31)
            // Range updated to 32 to match HTML
            for (let i = 0; i < 32; i++) {
                const card = data.cards[i];
                // Ensure card data exists for this index before trying to update
                if (card) {
                    const titleEl = document.getElementById(`card-title-${i}`);
                    if (titleEl) titleEl.textContent = card.title;

                    // Progress bar update logic removed

                    const textEl = document.getElementById(`card-text-${i}`);
                    if (textEl) textEl.textContent = card.text;

                    const statusLabelEl = document.getElementById(`card-status-label-${i}`);
                    if (statusLabelEl) statusLabelEl.textContent = card.lastUpdate;

                    const cardEl = document.getElementById(`card-${i}`);
                    if (cardEl) {
                        cardEl.classList.remove('status-1', 'status-2', 'status-0', "status-3");
                        cardEl.classList.add(`status-${card.status}`);
                    }

                    const iconEl = document.getElementById(`card-icon-${i}`);
                    if (iconEl) {
                        iconEl.className = `bi ${iconMap[card.status]}`;
                    }
                }
            }

            // --- Update KPIs (Simplified and Consolidated) ---
            const kpiIds = [
                'kpi-nopasanadape-status',
                'kpi-truecaptcha-balance',
                'kpi-zeptomail-balance',
                'kpi-twocaptcha-balance',
                'kpi-brightdata-balance',
                'kpi-googlecloud-balance',
                'kpi-cloudfare-status'
            ];

            kpiIds.forEach(id => {
                // Genera la clave JSON esperada (ej: kpi-active-threads -> kpi_active_threads)
                const dataKey = id.replace(/-/g, '_'); 
                if (data[dataKey]) {
                    updateElementContent(id, data[dataKey]);
                }
            });

            // --- Update New Scrape Data Table ---
            // Llama a la función para actualizar la nueva tabla de procesos
            updateScrapeData(data);


            const bottom_left = document.getElementById('activities-text-area');
            if (bottom_left && data.bottom_left) {
                bottom_left.value = data.bottom_left.join('\n');
            }
            
        })
        .catch(error => console.error('Error updating dashboard:', error));
}

setInterval(updateDashboard, 1000);
updateDashboard();