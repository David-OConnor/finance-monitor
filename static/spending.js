getEl("menu-spending").classList.add("menu-highlighted")
let HIGHLIGHTS = {by_cat: []}
let INCOME_TOTAL = 0.
let EXPENSES_TOTAL = 0.
let EXPENSES_DISCRETIONARY = 0.
let EXPENSES_NONDISCRET = 0.
let SPENDING_OVER_TIME = []
let INCOME_OVER_TIME = []
// let TRANSACTIONS = []
// Note: This is in days back. [start, end]. Consider switching to iso dates A/R.
let RANGE_SELECTED = [30, 0]

let ACTIVE_COLOR = "#349614"
let ACTIVE_WEIGHT = "bold"

// If we overrun this color list, it loops back to the top.
const PLOT_COLORS = [
    'rgb(255, 99, 132)',
    'rgb(54, 162, 235)',
    'rgb(187,255,86)',
    'rgb(86,255,255)',
    'rgb(199,86,255)',
    'rgb(255,137,86)',
    'rgb(255,86,227)',
    'rgb(86,255,204)',
    //
    'rgb(180,71,95)',
    'rgb(36,110,161)',
    'rgb(117,157,54)',
    'rgb(55,166,166)',
    'rgb(131,55,164)',
    'rgb(150,82,51)',
    'rgb(169,56,150)',
    'rgb(52,168,133)',

]

function setRangeFromDaysback(daysBack) {
    let activeBtn
    let inactiveBtns = []
    if (daysBack === 30) {
        activeBtn = getEl("range-30")
        inactiveBtns = [
            getEl("range-60"),
            getEl("range-90"),
            getEl("range-custom"),
        ]
    } else if (daysBack === 60) {
        activeBtn = getEl("range-60")
        inactiveBtns = [
            getEl("range-30"),
            getEl("range-90"),
            getEl("range-custom"),
        ]
    } else if (daysBack === 90) {
        activeBtn = getEl("range-90")
        inactiveBtns = [
            getEl("range-30"),
            getEl("range-60"),
            getEl("range-custom"),
        ]
    } else if (daysBack === -1) {
        activeBtn = getEl("range-custom")
        inactiveBtns = [
            getEl("range-30"),
            getEl("range-60"),
            getEl("range-90"),
        ]
    }

    activeBtn.style.color = ACTIVE_COLOR
    activeBtn.style.borderColor = ACTIVE_COLOR
    activeBtn.style.fontWeight = ACTIVE_WEIGHT

    for (let btn of inactiveBtns) {
        btn.style.color = null
        btn.style.borderColor = null
        btn.style.fontWeight = null
    }
    // todo: By-month buttons: Active indicator.

    if (daysBack === -1) {
        getEl("days-back").textContent = "(Custom range)"
    } else {
        getEl("days-back").textContent = "Past " + daysBack.toString() + " days"
    }

    let start, end
    if (daysBack === -1) {
        // auto
        const startDate = getEl("start").value
        const endDate = getEl("end").value
        start = parseInt((new Date() - new Date(startDate)) / (3600 * 1000*24))
        end = parseInt((new Date() - new Date(endDate)) / (3600 * 1000*24))
    } else {
        end = 0
        start = daysBack
    }

    setRange(start, end)
}

function setRange(start, end) {
    // Set the date range.
    console.log("in sr", start, end)
    RANGE_SELECTED = [start, end]

    const payload = {
        start: start,
        end: end,
    }

    fetch("/load-spending-data", { body: JSON.stringify(payload), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            HIGHLIGHTS = r.highlights
            INCOME_TOTAL = r.income_total
            EXPENSES_TOTAL = r.expenses_total
            EXPENSES_DISCRETIONARY = r.expenses_discretionary
            EXPENSES_NONDISCRET = r.expenses_nondiscret
            SPENDING_OVER_TIME = r.spending_over_time
            INCOME_OVER_TIME = r.income_over_time
            MERCHANTS_NEW = r.merchants_new

            // These 0 checks make sure we show "0" instead of "-0".
            getEl("income-total").textContent = formatAmount(INCOME_TOTAL, 0)
            getEl("expenses-total").textContent = formatAmount(EXPENSES_TOTAL === 0 ? 0 : -EXPENSES_TOTAL, 0)
            getEl("expenses-discretionary").textContent = formatAmount(EXPENSES_DISCRETIONARY === 0 ? 0 : -EXPENSES_DISCRETIONARY, 0)
            getEl("expenses-nondiscret").textContent = formatAmount(EXPENSES_NONDISCRET === 0 ? 0 : -EXPENSES_NONDISCRET, 0)

            populateTextData()

            setupPieCharts()
            setupTrendCharts()
        });
}

function populateTextData() {
    let sectionSpending = getEl("spending-section")
    sectionSpending.replaceChildren()

    for (let item of HIGHLIGHTS.by_cat) {
        let amountText = formatAmount(item[1][1])
        amountText = amountText.replace("-", "")

        let h4 = createEl(
            "h4",
            {},
            {marginTop: 0, marginBottom: 0, fontWeight: "normal", cursor: "pointer"},
            catDisp(item[0]) + ": "
        )
        let s = createEl("span", {class: "tran-neutral"},  {}, amountText)
        h4.appendChild(s)

        h4.addEventListener("click", _ => {
            loadTransactions(RANGE_SELECTED[0], RANGE_SELECTED[1], item[0])
        })

        sectionSpending.appendChild(h4)
    }

    let sectionChanges = getEl("change-section")
    sectionChanges.replaceChildren()
    for (let item of HIGHLIGHTS.cat_changes) {
        let amountText = formatAmount(item[1])
        if (item[1] > 0) {
            amountText = "+" + amountText
        }

        let h4 = createEl(
            "h4",
            {},
            {marginTop: 0, marginBottom: 0, fontWeight: "normal", cursor: "pointer"},
            catDisp(item[0]) + ": "

        )
        let s = createEl("span", {class: "tran-neutral"},  {}, amountText)
        h4.appendChild(s)

        h4.addEventListener("click", _ => {
            loadTransactions(RANGE_SELECTED[0], RANGE_SELECTED[1], item[0])
        })

        sectionChanges.appendChild(h4)
    }

    let newMerchants = getEl("new-merchants-section")
    newMerchants .replaceChildren()

    let h4
    if (MERCHANTS_NEW.length === 0 ) {
        h4 = createEl("h4", {}, {marginTop: 0, marginBottom: 0, fontWeight: "normal"}, "(None)")
        newMerchants.appendChild(h4)
    }

    for (let merchant of MERCHANTS_NEW) {
        h4 = createEl(
            "h4",
            {},
            {marginTop: 0, marginBottom: 0, fontWeight: "normal", marginLeft: "6px", cursor: "pointer"},
            merchant[0]
        )

        h4.addEventListener("click", _ => {
            loadTransactions(RANGE_SELECTED[0], RANGE_SELECTED[1], null, merchant[0])
        })

        if (merchant[1] !== null && merchant[1].length !== 0) {
            let d = createEl("div", {}, {display: "flex"})
            let img = createEl("img", {"src": merchant[1], alt: "", width: "24px"})
            d.appendChild(img)
            d.appendChild(h4)
            newMerchants.appendChild(d)
        } else {
            newMerchants.appendChild(h4)
        }
    }

}

function populateTransactions(transactions) {
    // Given a set of transactions, update the section listing them.
    let section = getEl("transactions")
    section.replaceChildren()

    const hStyle = {marginTop: 0, marginBottom: 0}

    for (let tran of transactions) {
        let el1 = createEl("div", {}, {gridColumn: "1/2"})
        let h1 = createEl("h4", {}, hStyle, tran.description)
        el1.appendChild(h1)
        section.appendChild(el1)

        let el2 = createEl("div", {}, {gridColumn: "2/3"})
        let h2 = createEl("h4", {}, hStyle, tran.institution_name)
        el2.appendChild(h2)
        section.appendChild(el2)

        let el3 = createEl("div", {}, {gridColumn: "3/4"})
        let h3 = createEl("h4", {}, hStyle, tran.amount)
        el3.appendChild(h3)
        section.appendChild(el3)

        let el4 = createEl("div", {}, {gridColumn: "4/5"})
        let h4 = createEl("h4", {}, hStyle, tran.date_display)
        el4.appendChild(h4)
        section.appendChild(el4)
    }
}

function loadTransactions(startDaysBack, endDaysBack, category, merchant) {
    // Load transactions based on date range, and/or category clicked.

    // RANGE_SELECTED is in days back; convert to ISO dates.

    // todo: Helper fn A/R
    let start = new Date();
    start.setDate(start.getDate() - startDaysBack);
    start = start.toISOString().split('T')[0];
    let end = new Date();
    end.setDate(end.getDate() - endDaysBack);
    end = end.toISOString().split('T')[0];

    const data = {
        start_i: null,
        end_i: null,
        search: merchant ? merchant : null, // todo: Set up on backend to filter by merchant; not just search.
        start: start,
        end: end,
        category: category,
    }

    fetch("/load-transactions", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
        .then(result => result.json())
        .then(r => {
            // TRANSACTIONS = r.transactions
            // let existingTranIds = TRANSACTIONS.map(t => t.id)

            // for (let tranLoaded of r.transactions) {
            //     // Don't add duplicates.
            //     // if (!existingTranIds.includes(tranLoaded.id)) {
            //         TRANSACTIONS.push(tranLoaded)
            //     }
            // }
            console.log("Loaded transactions: ", r.transactions)

            populateTransactions(r.transactions)
        });
}

function setupPieCharts() {
    // https://www.chartjs.org/docs/latest/charts/doughnut.html#doughnut

    // {#const config = {#}
    // {#    type: 'doughnut',#}
    // {#    data: data,#}

    const PCT_THRESH_GROUP = 0.04
    // todo:  YOu could use the alreayd passed income.
    // todo: Misc cat
    let total = 0
    for (let item of HIGHLIGHTS.by_cat) {
        total += item[1][1]
    }

    // Group minor contributors together.
    let labels = []
    let values = []
    let minorTotal = 0.
    for (let item of HIGHLIGHTS.by_cat) {
        let port = item[1][1] / total
        if (port > PCT_THRESH_GROUP) {
            labels.push(catDisp(item[0]))
            values.push(-item[1][1])
        } else {
            minorTotal += -item[1][1]
        }
    }
    labels.push("Other")
    values.push(minorTotal)



    // {#for (let item of HIGHLIGHTS.by_cat) {#}
    // {#    labels.push(catDisp(item[0]))#}
    // {#    values.push(item[1][1])#}
    //    {#}#}

    // getEl('plot').remove()

    let data_ = [{
        values: values,
        labels: labels,
        type: 'pie',
        textinfo: "label",
    }];

    let layout = {
        height: 420,
        width: 420,
        showlegend: false,
        margin: {
            l: 0,
            r: 0,
            b: 0,
            t: 0,
            pad: 0,

        },
        paper_bgcolor: "#F8F8F8",
    };

    if (typeof(Plotly) == "undefined") {
        loadPlotLibs()
        return
    }

    Plotly.newPlot('plot-wrapper', data_, layout, {displaylogo: false});

    // {##}
    // {##}
    // {#let el = document.createElement("canvas")#}
    // {#el.setAttribute("id", "plot")#}
    // {##}
    // {#document.addEventListener('DOMContentLoaded', function () {#}
    // {#    var ctx = document.getElementById('myPieChart').getContext('2d');#}
    // {#    // Your chart initialization code here#}
    // //
    // {#getEl("plot-wrapper").appendChild(el)#}
    // {##}
    // {#let chartArea = getEl('plot').getContext('2d')#}
    // {##}
    // {#const data = {#}
    // {#    labels: labels,#}
    // {#    datasets: [{#}
    // {#label: "Spending, by category",#}
    // {#        data: values,#}
    // {#        backgroundColor: PLOT_COLORS,#}
    // {#hoverOffset: 4#}
    // {#        //ackgroundColor: Utils.colors({#}
    // {#        //   color: Utils.color(0),#}
    // {#        //  count: 5#}
    // {#        //}),#}
    // {#        //data: Utils.numbers({#}
    // {#        //   count: 5,#}
    // {#        //  min: 0,#}
    // {#        // max: 100#}
    // {#        //}),#}
    // {#    }],#}
    // //
    // {##}
    // {#const chartSpendingPie = new Chart(chartArea, {#}
    // {#type: "pie",#}
    // {#    type: 'doughnut',#}
    // {#    data: data,#}
    // {#    options: {#}
    // {#        animation: false,#}
    // {#plugins: [ChartDataLabels],#}
    // {#        plugins: {#}
    // {#            legend: {#}
    // {#                display: false // This will hide the legend#}
    // {#            },#}
    // {#            // Configuration options for the datalabels plugin#}
    // {#            datalabels: {#}
    // {#                backgroundColor: function (context) {#}
    // {#                    return context.dataset.backgroundColor;#}
    // {#                },#}
    // {#                borderColor: 'white',#}
    // {#                borderRadius: 25,#}
    // {#                borderWidth: 2,#}
    // {#                color: 'white',#}
    // {#                display: function (context) {#}
    // {#                    let dataset = context.dataset;#}
    // {#                    let count = dataset.data.length;#}
    // {#                    let value = dataset.data[context.dataIndex];#}
    // {#                    return value > count * 1.5;#}
    // {#                },#}
    // {#                font: {#}
    // {#                    weight: 'bold'#}
    // {#                },#}
    // {#                padding: 6,#}
    // {#                formatter: Math.round,#}
    // {##}
    // {#                anchor: 'end',#}
    // {#                align: 'end',#}
    // {#                labels: {#}
    // {#                    color: 'blue'#}
    // {#                }#}
    // {#            }#}
    // {#        }#}
    // {#    }#}
    // //
    //
    //
    // {#    radius: 0, // Don't show circles on the points.#}
    // {#    responsive: true,#}
    // {#    scales: {#}
    // {#        x: {#}
    // {#            display: true,#}
    // {#            title: {#}
    // {#                display: true,#}
    // {#                text: 'Frequency (Hz)'#}
    // {#            },#}
    // {#            type: FREQ_LOG ? 'logarithmic' : 'linear',#}
    // {#            ticks: {#}
    // {#                stepSize: 500#}
    // {#            }#}
    // {#        },#}
    // {#        y: {#}
    // {#            title: {#}
    // {#                display: true,#}
    // {#                text: 'Amplitude and phase response'#}
    // {#            },#}
    // {#            display: true,#}
    // {#ticks: {#}
    // {#    stepSize: #}
    // {##}
    // {#        }#}
    // {#    },#}
    // {#    plugins: {#}
    // {#        title: {#}
    // {#            display: true,#}
    // {#            text: 'Filter response: Amplitude and phase'#}
    // {#        }#}
    // {#    },#}

}

function loadPlotLibs() {
    // Not in a script tag, because it's huge.

    let script = document.createElement('script');
    script.src = "../static/js_libs/plotly-basic-2.30.1.min.js";
    script.onload = function () {
        setupPieCharts()
    };
    document.head.appendChild(script);

    script = document.createElement('script');
    script.src = "../static/js_libs/chart.min.js";
    script.onload = function () {
        setupTrendCharts()
    };
    document.head.appendChild(script);
}

function setupTrendCharts() {
    // https://www.chartjs.org/docs/latest/charts/doughnut.html#doughnut

    // {#const config = {#}
    // {#    type: 'doughnut',#}
    // {#    data: data,#}

    // Set up spending over time.
    getEl('spending-over-time').remove()

    let el = document.createElement("canvas")
    el.setAttribute("id", "spending-over-time")
    getEl("spending-over-time-wrapper").appendChild(el)

    let chartArea = getEl('spending-over-time').getContext('2d')

    let labels = []
    let values = []
    for (let item of SPENDING_OVER_TIME) {
        labels.push(item[0])
        values.push(-item[1])
    }

    let data = {
        labels: labels,
        datasets: [{
            label: "Spending over time",
            data: values,
            backgroundColor: PLOT_COLORS,
            hoverOffset: 4
        }]
    };

    if (typeof(Chart) == "undefined") {
        return  // We handle loading these scripts together, from when Plotly is missing.
    }

    let chartSpending = new Chart(chartArea, {
        type: 'line',
        data: data,
        options: {
            animation: false,
            plugins: {
                legend: {
                    display: false // This will hide the legend
                }
            }
        }
    })

    // todo: DRY with above!

    // Set up net income over time
    getEl('income-over-time').remove()

    el = document.createElement("canvas")
    el.setAttribute("id", "income-over-time")
    getEl("income-over-time-wrapper").appendChild(el)

    chartArea = getEl('income-over-time').getContext('2d')

    labels = []
    values = []
    for (let i=0; i<INCOME_OVER_TIME.length; i++) {
        // {#for (item of INCOME_OVER_TIME) {#}
        labels.push(INCOME_OVER_TIME[i][0])
        values.push(INCOME_OVER_TIME[i][1] + SPENDING_OVER_TIME[i][1])
    }

    data = {
        labels: labels,
        datasets: [{
            label: "Net income over time",
            data: values,
            backgroundColor: PLOT_COLORS,
            hoverOffset: 4
        }]
    };

    let chartIncome = new Chart(chartArea, {
        type: 'line',
        data: data,
        options: {
            animation: false,
            plugins: {
                legend: {
                    display: false // This will hide the legend
                }
            }
        }
    })
}

function setDatePickerDefaults() {

    // Setup
    const today = new Date();

    // Subtract 30 days
    const thirtyDaysAgo = new Date(today.setDate(today.getDate() - 30));

    // Format the date as "YYYY-MM-DD"
    getEl("start").value = thirtyDaysAgo.toISOString().split('T')[0]
    getEl("end").value = (new Date()).toISOString().split('T')[0]
}

function setRangeWrapper(monthName, start, end) {
    // Converts dates to days back.
    // todo: These APIs are confusing; sort it out.
    start = parseInt((new Date() - new Date(start)) / (3600 * 1000*24))
    end = parseInt((new Date() - new Date(end)) / (3600 * 1000*24))

    // todo: DRY
    let inactiveBtns = [
        getEl("range-30"),
        getEl("range-60"),
        getEl("range-90"),
        getEl("range-custom"),
        // todo: Other single-months.
    ]

    for (let btn of inactiveBtns) {
        btn.style.color = null
        btn.style.borderColor = null
        btn.style.fontWeight = null
    }

    getEl("days-back").textContent = monthName

    // Mark the button using the active style
    // todo: DRY
    // {#let activeBtn = getEl("range-month-{{ item.0 }}").style#}
    // {#activeBtn.style.color = ACTIVE_COLOR#}
    // {#activeBtn.style.borderColor = ACTIVE_COLOR#}
    // {#activeBtn.style.fontWeight = ACTIVE_WEIGHT#}

    setRange(start, end)
}

function init() {
    setDatePickerDefaults()
    setRangeFromDaysback(30)
}

init()

