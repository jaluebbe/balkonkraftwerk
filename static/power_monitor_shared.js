/**
 * Shared functionality for Balkonkraftwerk power monitoring
 * Used by both index.html (cloud) and index_raspi.html (local)
 */

// Cache DOM elements
const elements = {
    connectionStatus: null,
    priceLevel: null,
    priceTotal: null,
    priceCurrency: null,
    meterConsumptionPower: null,
    meterConsumption: null,
    meterProductionPower: null,
    meterProduction: null,
    voltageL1: null,
    voltageL2: null,
    voltageL3: null,
    currentL1: null,
    currentL2: null,
    currentL3: null,
    powerL1: null,
    powerL2: null,
    powerL3: null,
    producerPower: null,
    batteryVoltage: null,
    batteryCurrent: null,
    batteryPower: null,
    consumerPower: null,
    unknownConsumersPower: null
};

// Global state
let ws = undefined;
let lastMessageUtc = undefined;
let lastSmartMeterUtc = undefined;
let gauge = null;

const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const noSleep = new NoSleep();

/**
 * Initialize DOM element references
 */
function initializeElements() {
    elements.connectionStatus = document.getElementById('connection_status');
    elements.priceLevel = document.getElementById('priceLevel');
    elements.priceTotal = document.getElementById('priceTotal');
    elements.priceCurrency = document.getElementById('priceCurrency');
    elements.meterConsumptionPower = document.getElementById('meterConsumptionPower');
    elements.meterConsumption = document.getElementById('meterConsumption');
    elements.meterProductionPower = document.getElementById('meterProductionPower');
    elements.meterProduction = document.getElementById('meterProduction');
    elements.voltageL1 = document.getElementById('voltageL1');
    elements.voltageL2 = document.getElementById('voltageL2');
    elements.voltageL3 = document.getElementById('voltageL3');
    elements.currentL1 = document.getElementById('currentL1');
    elements.currentL2 = document.getElementById('currentL2');
    elements.currentL3 = document.getElementById('currentL3');
    elements.powerL1 = document.getElementById('powerL1');
    elements.powerL2 = document.getElementById('powerL2');
    elements.powerL3 = document.getElementById('powerL3');
    elements.producerPower = document.getElementById('producerPower');
    elements.batteryVoltage = document.getElementById('batteryVoltage');
    elements.batteryCurrent = document.getElementById('batteryCurrent');
    elements.batteryPower = document.getElementById('batteryPower');
    elements.consumerPower = document.getElementById('consumerPower');
    elements.unknownConsumersPower = document.getElementById('unknownConsumersPower');
}

/**
 * Toggle visibility of elements by class name
 */
function toggle_by_class(cls, on) {
    const elements = document.getElementsByClassName(cls);
    for (let i = 0; i < elements.length; i++) {
        elements[i].style.display = on ? '' : 'none';
    }
}

/**
 * Set colspan attribute for elements by class name
 */
function colspan_by_class(cls, colSpan) {
    const elements = document.getElementsByClassName(cls);
    for (let i = 0; i < elements.length; i++) {
        elements[i].colSpan = colSpan;
    }
}

/**
 * Initialize the power gauge
 */
function initializeGauge() {
    const gaugeOpts = {
        angle: 0.1,
        lineWidth: 0.44,
        pointer: {
            length: 0.63,
            strokeWidth: 0.035
        },
        limitMax: true,
        limitMin: true,
        strokeColor: '#E0E0E0',
        staticLabels: {
            font: "14px sans-serif",
            labels: [-200, -150, -100, -50, 0, 50, 100, 150, 200],
            color: "#000000",
            fractionDigits: 0
        },
        renderTicks: {
            divisions: 8,
            divWidth: 1.6,
            divLength: 0.5,
            divColor: '#333333',
            subDivisions: 5,
            subLength: 0.3,
            subWidth: 0.4,
            subColor: '#666666'
        },
        staticZones: [{
                strokeStyle: "#30B32D",
                min: -200,
                max: 0
            }, // Green
            {
                strokeStyle: "#FFDD00",
                min: 0,
                max: 200
            } // Yellow
        ]
    };

    const canvasTarget = document.getElementById('canvas-preview');
    gauge = new Gauge(canvasTarget).setOptions(gaugeOpts);
    gauge.maxValue = 200;
    gauge.setMinValue(-200);
    gauge.set(0);
}

/**
 * Process meter consumption data
 */
function processMeterConsumption(message) {
    if (message.accumulatedConsumption == null ||
        message.accumulatedConsumption != null &&
        message.accumulatedProduction != null &&
        message.accumulatedConsumption + message.accumulatedProduction > 0
    ) {
        elements.meterConsumption.innerHTML = parseFloat(message.lastMeterConsumption).toFixed(2);
        elements.meterProduction.innerHTML = parseFloat(message.lastMeterProduction).toFixed(2);
        toggle_by_class("meterConsumptionAvailable", true);
    } else {
        toggle_by_class("meterConsumptionAvailable", false);
    }
}

/**
 * Process meter power data and update gauge
 */
function processMeterPower(message) {
    const consumptionPower = parseFloat(message.power);
    const productionPower = parseFloat(message.powerProduction);
    gauge.set(consumptionPower - productionPower);

    let extendedDataAvailable = false;
    let phaseColSpan = 4;

    if (message.voltagePhase1 != null) {
        elements.voltageL1.innerHTML = parseFloat(message.voltagePhase1).toFixed(1);
        elements.voltageL2.innerHTML = parseFloat(message.voltagePhase2).toFixed(1);
        elements.voltageL3.innerHTML = parseFloat(message.voltagePhase3).toFixed(1);
        extendedDataAvailable = true;
        phaseColSpan -= 1;
        toggle_by_class("voltageLabel", true);
    } else {
        toggle_by_class("voltageLabel", false);
    }

    if (message.currentL1 != null) {
        elements.currentL1.innerHTML = parseFloat(message.currentL1).toFixed(2);
        elements.currentL2.innerHTML = parseFloat(message.currentL2).toFixed(2);
        elements.currentL3.innerHTML = parseFloat(message.currentL3).toFixed(2);
        extendedDataAvailable = true;
        phaseColSpan -= 1;
        toggle_by_class("currentLabel", true);
    } else {
        toggle_by_class("currentLabel", false);
    }

    if (message.powerL1 != null) {
        elements.powerL1.innerHTML = parseFloat(message.powerL1).toFixed(1);
        elements.powerL2.innerHTML = parseFloat(message.powerL2).toFixed(1);
        elements.powerL3.innerHTML = parseFloat(message.powerL3).toFixed(1);
        extendedDataAvailable = true;
        phaseColSpan -= 1;
        toggle_by_class("powerLabel", true);
    } else {
        toggle_by_class("powerLabel", false);
    }

    toggle_by_class("singlePhaseData", extendedDataAvailable);
    if (phaseColSpan < 4) {
        colspan_by_class("phaseLabel", phaseColSpan);
    }

    elements.meterConsumptionPower.innerHTML = consumptionPower;
    elements.meterProductionPower.innerHTML = productionPower;
}

/**
 * Process general message data (producer, consumer, battery, price)
 */
function processMessage(message) {
    elements.producerPower.innerHTML = message.producer_power;
    elements.consumerPower.innerHTML = message.consumer_power;

    if (message.unknown_consumers_power != null) {
        elements.unknownConsumersPower.innerHTML = message.unknown_consumers_power;
        toggle_by_class("unknownData", true);
    } else {
        toggle_by_class("unknownData", false);
    }

    if (message.battery_inverter != undefined) {
        elements.batteryPower.innerHTML = message.battery_power;
        elements.batteryVoltage.innerHTML = message.battery_inverter.dc_voltage;
        elements.batteryCurrent.innerHTML = message.battery_inverter.dc_current;
        toggle_by_class("batteryData", true);
    } else {
        toggle_by_class("batteryData", false);
    }

    if (message.tibber_price != undefined) {
        elements.priceLevel.innerHTML = message.tibber_price.level;
        elements.priceTotal.innerHTML = parseFloat(message.tibber_price.total).toFixed(2);
        elements.priceCurrency.innerHTML = message.tibber_price.currency;
        toggle_by_class("priceData", true);
    } else {
        toggle_by_class("priceData", false);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(event) {
    const utcNow = Date.now() / 1e3;
    elements.connectionStatus.innerHTML = "Connected";
    const message = JSON.parse(event.data);

    if (message.type === "electricity_meter") {
        processMeterConsumption(message);
        if (lastSmartMeterUtc == null || utcNow - lastSmartMeterUtc > 30) {
            processMeterPower(message);
        }
    } else if (message.type === "smart_meter") {
        lastSmartMeterUtc = message.utc;
        processMeterPower(message);
    } else {
        processMessage(message);
    }
    lastMessageUtc = message.utc;
}

/**
 * Check connection health and reconnect if needed
 */
function checkConnection() {
    const utcNow = Date.now() / 1e3;
    if (lastMessageUtc != null && utcNow - lastMessageUtc > 30) {
        ws.onclose = null;
        ws.onmessage = null;
        ws.close(1000);
        connect();
    }
}

/**
 * Setup event handlers (must be called after DOM is loaded)
 */
function setupEventHandlers() {
    onfocus = (event) => {
        checkConnection();
    };

    document.addEventListener('click', function enableNoSleep() {
        document.removeEventListener('click', enableNoSleep, false);
        noSleep.enable();
    }, false);
}

/**
 * Initialize the application
 */
function initialize() {
    initializeElements();
    initializeGauge();
    setupEventHandlers();
}
