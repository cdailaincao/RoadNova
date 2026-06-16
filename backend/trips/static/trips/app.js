// RoadNova app.js — optional chaining replaced with safe fallbacks

const cityData = JSON.parse(document.getElementById('city-data').textContent);
const cityMap = Object.fromEntries(cityData.map((city) => [city.slug, city]));
const form = document.getElementById('trip-form');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const costsEl = document.getElementById('costs');
const itineraryEl = document.getElementById('itinerary-list');
const weatherEl = document.getElementById('weather-list');
const routeSummaryEl = document.getElementById('route-summary');
const splitOutputEl = document.getElementById('split-output');
const expenseListEl = document.getElementById('expense-list');
const poiResultsEl = document.getElementById('poi-results');
const expenses = [];
let latestPlan = null;
let map;
let routeLayer;

function iconRefresh() {
    if (window.lucide) window.lucide.createIcons();
}

function rupee(value) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0,
    }).format(value);
}

function showPanel(name) {
    document.querySelectorAll('.view-panel').forEach(function(panel) {
        panel.classList.toggle('is-active', panel.dataset.panel === name);
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (name === 'map' && map) {
        setTimeout(function() {
            map.invalidateSize();
            var routeCities = latestPlan ? latestPlan.route : [cityMap.bangalore, cityMap.goa];
            drawRoute(routeCities);
        }, 120);
    }
    iconRefresh();
}

function initMap() {
    if (!window.L) { setTimeout(initMap, 250); return; }
    map = L.map('map', { scrollWheelZoom: false }).setView([20.5937, 78.9629], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    drawRoute([cityMap.bangalore, cityMap.goa]);
}

async function drawRoute(routeCities) {
    if (!map || !routeCities.length) return;
    if (routeLayer) routeLayer.remove();
    var points = routeCities.map(function(city) { return [city.lat, city.lon]; });
    routeLayer = L.layerGroup().addTo(map);
    var coordinates = routeCities.map(function(city) { return city.lon + ',' + city.lat; }).join(';');
    try {
        var response = await fetch(
            'https://router.project-osrm.org/route/v1/driving/' + coordinates + '?overview=full&geometries=geojson'
        );
        var route = await response.json();
        var geometry = null;
        if (route.routes && route.routes[0] && route.routes[0].geometry) {
            geometry = route.routes[0].geometry.coordinates;
        }
        if (!geometry) throw new Error('No route geometry');
        L.geoJSON({ type: 'LineString', coordinates: geometry }, {
            style: { color: '#D4500A', weight: 5, opacity: 0.9 },
        }).addTo(routeLayer);
    } catch (error) {
        L.polyline(points, { color: '#D4500A', weight: 5, opacity: 0.8, dashArray: '8 8' }).addTo(routeLayer);
    }
    routeCities.forEach(function(city, index) {
        var label = index === 0 ? 'Start' : index === routeCities.length - 1 ? 'Finish' : 'Night ' + index;
        L.marker([city.lat, city.lon]).addTo(routeLayer).bindPopup('<strong>' + label + '</strong>: ' + city.name);
    });
    map.fitBounds(points, { padding: [40, 40] });
}

function renderCosts(costs) {
    var items = [
        ['Fuel', costs.fuel],
        ['Tolls', costs.tolls],
        ['Hotels', costs.hotels],
        ['Food', costs.food],
        ['Total', costs.total],
        ['Per person', costs.per_person],
    ];
    costsEl.innerHTML = items.map(function(item) {
        return '<div class="metric"><span>' + item[0] + '</span><strong>' + rupee(item[1]) + '</strong></div>';
    }).join('');
}

function renderItinerary(plan) {
    itineraryEl.innerHTML = plan.itinerary.map(function(day) {
        var driveBlocks = day.drive_blocks.map(function(block) {
            return '<div class="drive-step"><span>' + block.label + ' &mdash; ' + block.distance + '</span><p>' + block.text + '</p></div>';
        }).join('');
        return '<article class="day-card">' +
            '<span>Day ' + day.day + ' &mdash; ' + day.date + ' &mdash; ' + day.city + ', ' + day.state + '</span>' +
            '<h3>' + day.title + '</h3>' +
            '<div class="drive-timeline">' + driveBlocks + '</div>' +
            '<div class="day-grid">' +
            '<div><span>Morning</span>' + day.morning + '</div>' +
            '<div><span>Afternoon</span>' + day.afternoon + '</div>' +
            '<div><span>Evening</span>' + day.evening + '</div>' +
            '</div>' +
            '<p><strong>Stay:</strong> ' + day.hotel + '. <strong>Food:</strong> ' + day.restaurant + '. <strong>Road note:</strong> ' + day.drive_note + '</p>' +
            '</article>';
    }).join('');
}

async function loadWeather(routeCities, days) {
    weatherEl.textContent = 'Loading live weather from Open-Meteo...';
    var forecastDays = Math.min(days, 7);
    var forecasts = await Promise.all(routeCities.map(async function(city) {
        try {
            var localReport = await fetch(
                '/api/weather-point/?name=' + encodeURIComponent(city.name) + '&lat=' + city.lat + '&lon=' + city.lon + '&days=' + forecastDays
            ).then(function(r) { return r.json(); });
            if (!localReport.error) return localReport;
            var params = new URLSearchParams({
                latitude: city.lat,
                longitude: city.lon,
                daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                timezone: 'Asia/Kolkata',
                forecast_days: forecastDays,
            });
            var liveReport = await fetch('https://api.open-meteo.com/v1/forecast?' + params).then(function(r) { return r.json(); });
            var daily = liveReport.daily || {};
            return {
                city: city.name,
                forecast: (daily.time || []).map(function(date, i) {
                    return {
                        date: date,
                        max_c: daily.temperature_2m_max ? daily.temperature_2m_max[i] : null,
                        min_c: daily.temperature_2m_min ? daily.temperature_2m_min[i] : null,
                        rain_pct: daily.precipitation_probability_max ? (daily.precipitation_probability_max[i] || 0) : 0,
                        code: daily.weather_code ? daily.weather_code[i] : null,
                    };
                }),
            };
        } catch (e) {
            return { city: city.name, error: 'Live weather unavailable right now.' };
        }
    }));
    weatherEl.classList.remove('empty-msg');
    weatherEl.innerHTML = forecasts.map(function(report) {
        if (report.error) {
            return '<div class="weather-day"><span>' + report.city + '</span><strong>Unavailable</strong>' + report.error + '</div>';
        }
        var first = report.forecast[0];
        return '<div class="weather-day"><span>' + report.city + '</span><strong>' + first.min_c + '°C — ' + first.max_c + '°C</strong>Rain chance ' + (first.rain_pct || 0) + '% today</div>';
    }).join('');
}

function renderSplit() {
    if (!latestPlan) return;
    var extra = expenses.reduce(function(sum, item) { return sum + item.amount; }, 0);
    var total = latestPlan.costs.total + extra;
    splitOutputEl.classList.remove('empty-msg');
    splitOutputEl.innerHTML =
        '<div class="metric"><span>Total with extras</span><strong>' + rupee(total) + '</strong></div>' +
        '<div class="metric"><span>Each traveller pays</span><strong>' + rupee(Math.round(total / latestPlan.travelers)) + '</strong></div>';
    expenseListEl.innerHTML = expenses.map(function(item) {
        return '<li>' + item.name + ': <strong>' + rupee(item.amount) + '</strong></li>';
    }).join('');
}

function updateSos(plan) {
    var contact = document.getElementById('emergency-contact').value.trim();
    var callTarget = contact || plan.emergency.primary;
    document.getElementById('sos-call').href = 'tel:' + callTarget;
}

async function planTrip() {
    var data = new FormData(form);
    var payload = {
        origin: data.get('origin'),
        destination: data.get('destination'),
        start_date: data.get('start_date'),
        end_date: data.get('end_date'),
        travelers: data.get('travelers'),
        mileage: data.get('mileage'),
        interests: data.getAll('interests'),
    };
    costsEl.innerHTML = '<div class="metric"><span>Status</span><strong>Planning your trip...</strong></div>';
    itineraryEl.innerHTML = '<div class="empty-msg">Generating your itinerary...</div>';
    var response = await fetch('/api/plan/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload),
    });
    var plan = await response.json();
    if (!response.ok) {
        costsEl.innerHTML = '<div class="metric"><span>Error</span><strong>' + plan.error + '</strong></div>';
        itineraryEl.innerHTML = '<div class="empty-msg">' + plan.error + '</div>';
        weatherEl.innerHTML = '<div class="empty-msg">Weather loads after a valid trip plan.</div>';
        splitOutputEl.innerHTML = '<div class="empty-msg">Group split appears after a valid trip plan.</div>';
        latestPlan = null;
        return;
    }
    latestPlan = plan;
    routeSummaryEl.textContent = plan.origin + ' to ' + plan.destination + ' - ' + plan.days + ' days';

    // Update Google Maps deep-link with actual route waypoints
    var gmapsBtn = document.getElementById('open-gmaps-btn');
    if (gmapsBtn && plan.route && plan.route.length) {
        var waypoints = plan.route.map(function(city) {
            return encodeURIComponent(city.name + ', India');
        });
        var gmapsUrl = 'https://www.google.com/maps/dir/' + waypoints.join('/');
        gmapsBtn.href = gmapsUrl;
    }

    drawRoute(plan.route);
    renderCosts(plan.costs);
    renderItinerary(plan);
    renderSplit();
    updateSos(plan);
    await loadWeather(plan.route, plan.days);
    iconRefresh();
}

async function loadPois() {
    var city = document.getElementById('poi-city').value;
    var category = document.getElementById('poi-category').value;
    poiResultsEl.textContent = 'Searching OpenStreetMap...';
    var report = await fetch('/api/pois/?city=' + city + '&category=' + category).then(function(r) { return r.json(); });
    if (!report.pois.length) {
        poiResultsEl.innerHTML = '<div class="poi-item"><strong>No live results found</strong><span>' + report.city + '</span>Try another category or city.</div>';
        return;
    }
    poiResultsEl.innerHTML = report.pois.map(function(poi) {
        return '<div class="poi-item"><strong>' + poi.name + '</strong><span>' + report.city + ' - ' + report.category + '</span></div>';
    }).join('');
}

function initRentalTabs() {
    var tabs = document.querySelectorAll('.rental-tab');
    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            tabs.forEach(function(t) { t.classList.remove('active'); });
            tab.classList.add('active');
            var target = tab.dataset.tab;
            document.querySelectorAll('.rental-panel').forEach(function(panel) {
                panel.classList.toggle('hidden', panel.id !== 'tab-' + target);
            });
            iconRefresh();
        });
    });
}

form.addEventListener('submit', function(e) {
    e.preventDefault();
    planTrip();
});

document.querySelectorAll('[data-view]').forEach(function(btn) {
    btn.addEventListener('click', function() { showPanel(btn.dataset.view); });
});

document.getElementById('load-pois').addEventListener('click', loadPois);

document.getElementById('add-expense').addEventListener('click', function() {
    var nameInput = document.getElementById('expense-name');
    var amountInput = document.getElementById('expense-amount');
    var amount = Number(amountInput.value || 0);
    if (!amount || amount < 0) return;
    expenses.push({ name: nameInput.value.trim() || 'Shared expense', amount: amount });
    nameInput.value = '';
    amountInput.value = '';
    renderSplit();
});

document.getElementById('emergency-contact').addEventListener('input', function() {
    if (latestPlan) updateSos(latestPlan);
});

document.addEventListener('DOMContentLoaded', function() {
    initMap();
    initRentalTabs();
    iconRefresh();
});
/* ═══════════════════════════════════════════
   DATE SYNC — all date inputs stay in sync
═══════════════════════════════════════════ */
(function initDateSync() {
    // All date input IDs across every panel
    const START_IDS = ['rental-start', 'car-rental-start'];
    const END_IDS = ['rental-end', 'car-rental-end'];
    const FORM_START = document.querySelector('input[name="start_date"]');
    const FORM_END = document.querySelector('input[name="end_date"]');

    function syncStartDates(val) {
        START_IDS.forEach(function(id) {
            var el = document.getElementById(id);
            if (el && el.value !== val) el.value = val;
        });
    }

    function syncEndDates(val) {
        END_IDS.forEach(function(id) {
            var el = document.getElementById(id);
            if (el && el.value !== val) el.value = val;
        });
    }

    // Planner form → rentals
    if (FORM_START) {
        FORM_START.addEventListener('change', function() { syncStartDates(this.value); });
    }
    if (FORM_END) {
        FORM_END.addEventListener('change', function() { syncEndDates(this.value); });
    }

    // Rental bike start → others
    START_IDS.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', function() {
                var val = this.value;
                if (FORM_START && FORM_START.value !== val) FORM_START.value = val;
                syncStartDates(val);
            });
        }
    });

    // Rental bike end → others
    END_IDS.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', function() {
                var val = this.value;
                if (FORM_END && FORM_END.value !== val) FORM_END.value = val;
                syncEndDates(val);
            });
        }
    });
})();

/* ═══════════════════════════════════════════
   CAROUSEL FILTER TABS
═══════════════════════════════════════════ */
(function initCarouselFilterTabs() {
    var tabs = document.querySelectorAll('.carousel-filter-tab');
    var track = document.getElementById('dest-carousel-track');
    if (!tabs.length || !track) return;

    var allCards = Array.from(track.querySelectorAll('.dest-card'));

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            // Active state
            tabs.forEach(function(t) { t.classList.remove('active'); });
            tab.classList.add('active');

            // Scroll tab into view
            tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });

            var filter = tab.dataset.filter;

            // Show/hide cards
            allCards.forEach(function(card) {
                var tag = card.querySelector('.dest-card-tag');
                var tagText = tag ? tag.textContent.trim() : '';
                if (filter === 'all' || tagText === filter) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });

            // Reset carousel position
            track.style.transition = 'none';
            track.style.transform = 'translateX(0px)';
            setTimeout(function() { track.style.transition = ''; }, 50);

            // Reset dots
            var dots = document.querySelectorAll('.carousel-dot');
            dots.forEach(function(d, i) { d.classList.toggle('active', i === 0); });
        });
    });
})();
(function initScenery() {
    const destinations = [
        'Ladakh', 'Kerala', 'Coorg', 'Rajasthan', 'Goa', 'Spiti Valley', 'Pondicherry', 'Manali',
        'Uttarakhand', 'Himachal Pradesh', 'Hampi', 'Munnar'
    ];
    const slides = document.querySelectorAll('.scenery-slide');
    const destName = document.getElementById('scenery-dest-name');
    if (!slides.length) return;

    let current = 0;

    function showSlide(idx) {
        slides[current].classList.remove('active');
        current = (idx + slides.length) % slides.length;
        slides[current].classList.add('active');
        if (destName) {
            destName.style.opacity = '0';
            setTimeout(() => {
                destName.textContent = destinations[current] || '';
                destName.style.opacity = '1';
            }, 600);
        }
    }

    // Auto-advance every 5 seconds
    setInterval(() => showSlide(current + 1), 5000);
})();

/* ═══════════════════════════════════════════
   DESTINATION CAROUSEL
═══════════════════════════════════════════ */
(function initDestCarousel() {
    const track = document.getElementById('dest-carousel-track');
    const prevBtn = document.getElementById('carousel-prev');
    const nextBtn = document.getElementById('carousel-next');
    const dotsContainer = document.getElementById('carousel-dots');
    if (!track) return;

    const cards = track.querySelectorAll('.dest-card');
    const CARD_WIDTH = 320; // card (300) + gap (20)
    const VISIBLE = Math.floor(window.innerWidth / CARD_WIDTH) || 1;
    const TOTAL = cards.length;
    const MAX_IDX = Math.max(0, TOTAL - VISIBLE);

    let current = 0;
    let startX = 0;
    let isDragging = false;
    let dragOffset = 0;

    // Build dots
    const dotCount = MAX_IDX + 1;
    const dots = [];
    for (let i = 0; i <= MAX_IDX; i++) {
        const d = document.createElement('button');
        d.className = 'carousel-dot' + (i === 0 ? ' active' : '');
        d.setAttribute('aria-label', 'Slide ' + (i + 1));
        d.addEventListener('click', () => goTo(i));
        dotsContainer.appendChild(d);
        dots.push(d);
    }

    function goTo(idx) {
        current = Math.max(0, Math.min(idx, MAX_IDX));
        const offset = -(current * CARD_WIDTH);
        track.style.transform = `translateX(${offset}px)`;
        dots.forEach((d, i) => d.classList.toggle('active', i === current));
    }

    if (prevBtn) prevBtn.addEventListener('click', () => goTo(current - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => goTo(current + 1));

    // Drag / swipe
    track.addEventListener('mousedown', e => {
        isDragging = true;
        startX = e.clientX;
        dragOffset = 0;
        track.style.transition = 'none';
    });
    window.addEventListener('mousemove', e => {
        if (!isDragging) return;
        dragOffset = e.clientX - startX;
        const base = -(current * CARD_WIDTH);
        track.style.transform = `translateX(${base + dragOffset}px)`;
    });
    window.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        track.style.transition = '';
        if (dragOffset < -60) goTo(current + 1);
        else if (dragOffset > 60) goTo(current - 1);
        else goTo(current);
    });
    // Touch
    track.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
        dragOffset = 0;
    }, { passive: true });
    track.addEventListener('touchmove', e => {
        dragOffset = e.touches[0].clientX - startX;
        const base = -(current * CARD_WIDTH);
        track.style.transition = 'none';
        track.style.transform = `translateX(${base + dragOffset}px)`;
    }, { passive: true });
    track.addEventListener('touchend', () => {
        track.style.transition = '';
        if (dragOffset < -60) goTo(current + 1);
        else if (dragOffset > 60) goTo(current - 1);
        else goTo(current);
    });

    // "Plan route →" buttons navigate to the planner
    track.querySelectorAll('.btn-dest-plan').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            // Switch to planner view
            document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('is-active'));
            const plannerPanel = document.querySelector('[data-panel="planner"]');
            if (plannerPanel) plannerPanel.classList.add('is-active');
            // Pre-fill selects if slugs match
            const originSlug = btn.dataset.origin;
            const destSlug = btn.dataset.dest;
            const originSel = document.querySelector('select[name="origin"]');
            const destSel = document.querySelector('select[name="destination"]');
            if (originSel && originSlug) {
                const opt = originSel.querySelector(`option[value="${originSlug}"]`);
                if (opt) originSel.value = originSlug;
            }
            if (destSel && destSlug) {
                const opt = destSel.querySelector(`option[value="${destSlug}"]`);
                if (opt) destSel.value = destSlug;
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
})();