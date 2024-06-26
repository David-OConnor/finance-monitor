// This module contains code related to UI interactions on the Dashboard.

// Global mutal variables
let LINK_TOKEN = ""
let SEARCH_TEXT = ""
let FILTER_START = "1999-09-09"
let FILTER_END = "2040-09-09"
let FILTER_CAT = null
let VALUE_THRESH = 0
let CURRENT_PAGE = 0
let CAT_QUICKEDIT = null  // DB ID of the transaction we are quick-editing
// If true, always recategorize the currently quickediting item, based on description, and selected cat.
let CAT_ALWAYS = false
let QUICK_CAT_SEARCH = ""

// Whenever we change page, or filter terms, we may need to load transactions. This tracks
// if we've already done so, for a given config
let TRANSACTIONS_LOADED = true

const PAGE_SIZE = 60

const HIGHLIGHT_COLOR = "#fffbdb"
const FEE_COLOR = "#fff0ff"
const IGNORED_COLOR = "#bbbbbb"
const COLOR_HIGH_AMOUNT = "#c56926"

// Color transactions in value in excess of this. (todo: Make customizable)
const THRESH_HIGH_AMOUNT = 200

// Show this many items in the highlights category, per section.
const HIGHLIGHTS_SIZE = 5


// let TRANSACTIONS_DISPLAYED = []
let TRANSACTION_ICONS = true
let EDIT_MODE_TRAN = false

// We use an object vice map for serialization compatibility.
let TRANSACTIONS_UPDATED = {}
let ACCOUNTS_UPDATED = {}
let SPLIT_TRAN_ID = null
let NUM_NEW_SPLITS = 0

// See models.py
const ACC_TYPE_CHECKING = 0
const ACC_TYPE_SAVINGS = 1
const ACC_TYPE_DEBIT = 2
const ACC_TYPE_CREDIT = 3
const ACC_TYPE_401K = 4
const ACC_TYPE_STUDENT = 5
const ACC_TYPE_MORTGAGE = 6
const ACC_TYPE_CD = 7
const ACC_TYPE_MONEY_MARKET = 8
const ACC_TYPE_IRA = 9
const ACC_TYPE_MUTUAL_FUND = 10
const ACC_TYPE_CRYPTO = 11
const ACC_TYPE_ASSET = 12
const ACC_TYPE_BROKERAGE = 13
const ACC_TYPE_ROTH = 14


function getPublicToken() {
    // Launches a Plaid-controlled window to link to an account, using an already-retrieved link token.
    // After the user enters information, sends the public token to the backend, which exchanges it for
    // an access token. This is then stored in the database, associated with the user's account at
    // the linked institution.

    // Load the plaid script dynamically, so it doesn't load every time, or at page load.
    try {
        Plaid
    } catch (e) {
        let scriptEl = createEl("script", {src: "https://cdn.plaid.com/link/v2/stable/link-initialize.js"})

        scriptEl.onload = () => {
            getPublicToken() // Recursion; hopefully passing next time around
        }
        document.body.appendChild(scriptEl)
        return
    }

    console.log("In getPublicToken") // todo: To TS re-linking not working correctly.

    let handler = Plaid.create({
        // Create a new link_token to initialize Link
        // token: await fetch("/create_link_token", {...FETCH_HEADERS_POST }).link_token,
        token: LINK_TOKEN,
        onLoad: function() {
            // Optional, called when Link loads
            console.log("onLoad") // todo temp
        },
        onSuccess: function(public_token, metadata) {
            // Send the public_token to your app server.
            // The metadata object contains info about the institution the
            // user selected and the account ID or IDs, if the
            // Account Select view is enabled.
            // $.post('/exchange_public_token', {
            //     public_token: public_token,
            // });
            //
            const payload = {
                public_token: public_token,
                metadata: metadata
            }

            fetch("/exchange-public-token", { body: JSON.stringify(payload), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    if (r.success) {
                        console.log("Token exchange complete")
                        window.location.reload();
                    } else {
                        console.error("Token exchange failed")
                    }
                });
        },
        onExit: function(err, metadata) {
            // The user exited the Link flow.
            if (err != null) {
                // The user encountered a Plaid API error prior to exiting.
            }
            // metadata contains information about the institution
            // that the user selected and the most recent API request IDs.
            // Storing this information can be helpful for support.
        },
        onEvent: function(eventName, metadata) {
            // Optionally capture Link flow events, streamed through
            // this callback as your users connect an Item to Plaid.
            // For example:
            // eventName = "TRANSITION_VIEW"
            // metadata  = {
            //   link_session_id: "123-abc",
            //   mfa_type:        "questions",
            //   timestamp:       "2017-09-14T14:42:19.350Z",
            //   view_name:       "MFA",
            // }
        }
    });

    handler.open();
}

function filterTransactions() {
    // Filter transactions by keyword, date, value, category, etc. Sort by date at the end.
    const searchText = SEARCH_TEXT
    const valueThresh = VALUE_THRESH
    let start = new Date("1999-09-09")
    let end = new Date("2099-09-09")

    // Start and end will be empty strings if null
    if (FILTER_START.length) {
        start = new Date(FILTER_START)
    }
    if (FILTER_END.length) {
        end = new Date(FILTER_END)
    }

    let transactions = TRANSACTIONS

    // -2 is the "any" selection of the main filter.
    if (FILTER_CAT !== null && FILTER_CAT !== -2) {
        transactions = transactions.filter(t => t.category === FILTER_CAT)
    }

    // Note: This truthy statement catches both an empty string, and an undefined we get on init.
    if (searchText) {
        transactions = transactions.filter(t => {
            return t.description.toLowerCase().includes(searchText) ||
                t.notes.toLowerCase().includes(searchText) ||
                t.institution_name.toLowerCase().includes(searchText) ||
                t.merchant.toLowerCase().includes(searchText) ||
                catNameFromVal(t.category).toLowerCase().includes(searchText)
        })
    }

    transactions = transactions.filter(t => {
        let tran_date = new Date(t.date)
        return tran_date >= start && tran_date <= end
    })

    if (valueThresh) {
        transactions = transactions.filter(t => Math.abs(t.amount) >= valueThresh)
    }

    transactions.sort((b, a) => {
        // This sort by date, then DB ID prevents rows shifting for like dates.
        if (a.date === b.date) {
            return a.id - b.id
        }
        return new Date(a.date) - new Date(b.date)
    })

    const startI = CURRENT_PAGE * PAGE_SIZE
    const endI = CURRENT_PAGE * PAGE_SIZE + PAGE_SIZE

    transactions = transactions.slice(startI, endI)

    if (!TRANSACTIONS_LOADED) {  // A check against doing this multiple times (or finititely) in a row.
        TRANSACTIONS_LOADED = true

        // If, after filtering, we don't have a full page of information, request more from the backend.
        if (transactions.length < PAGE_SIZE) {
            console.log("Requesting more transactions...")
            const data = {
                start_i: startI,
                end_i: endI,
                search: SEARCH_TEXT,
                start: FILTER_START,
                end: FILTER_END,
                category: FILTER_CAT,
            }

            fetch("/load-transactions", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {
                    let existingTranIds = TRANSACTIONS.map(t => t.id)

                    for (let tranLoaded of r.transactions) {
                        // Don't add duplicates.
                        if (!existingTranIds.includes(tranLoaded.id)) {
                            TRANSACTIONS.push(tranLoaded)
                        }
                    }

                    refreshTransactions()
                });
        }
    }

    return transactions
}

function createAccRow(acc, type) {
    // Helper function when creating the account display.
    let div = createEl("div", {}, {display: "flex", justifyContent: "space-between", cursor: "pointer"})

    let name
    if (acc.manual) {
        name = acc.name
    } else {
        if (acc.nickname.length) {
            name = acc.nickname
        } else {
            // name = acc.name + " " + acc.name_official
            name = acc.name
        }
    }

    // Flex and align items for the health indicator
    let h_a = createEl("h4", {class: "acct-hdg"}, {marginRight: "26px", display: "flex", alignItems: "center"}, name)

    let val = acc.value
    if (["Credit", "Loan"].includes(type)) {
        val *= -1
    }

    const valClass = val > 0 ? "tran-pos" : "tran-neg"

    // Format with a comma, and no decimal places
    const valueFormatted = formatAmount(val, false)
    let h_b = createEl("h4", {class: "acct-hdg " + valClass}, {}, valueFormatted)

    for (let health of ACC_HEALTH) {
        if (health[0] === acc.id) {
            let healthIndicator = "🔴"
            if (health[1]) {
                healthIndicator = "🟢"
            }
            if (acc.needs_attention) {
                healthIndicator = "⚠️"
            }
            // todo: Allow repairing broken accs.


            let healthSpan = createEl("span", {}, {fontSize: "0.6em", marginRight: "4px"}, healthIndicator)
            h_a.prepend(healthSpan)
        }
    }

    div.appendChild(h_a)
    div.appendChild(h_b)

    div.addEventListener("click", _ => {
        setupAccEditForm(acc.id)
    })

    return div
}

function refreshAccounts() {
    //[Re]populate the accounts section based on state.

    console.log("Refreshing accounts...")

    let section = getEl("accounts")
    section.replaceChildren()

    const acc_cash = ACCOUNTS.filter(acc => [ACC_TYPE_CHECKING, ACC_TYPE_SAVINGS].includes(acc.sub_type))
    const acc_investment = ACCOUNTS.filter(acc => [ACC_TYPE_MUTUAL_FUND, ACC_TYPE_401K, ACC_TYPE_CD, ACC_TYPE_MONEY_MARKET,
        ACC_TYPE_BROKERAGE, ACC_TYPE_ROTH, ACC_TYPE_IRA].includes(acc.sub_type))

    const acc_credit = ACCOUNTS.filter(acc => [ACC_TYPE_CREDIT, ACC_TYPE_DEBIT].includes(acc.sub_type))
    const acc_loan = ACCOUNTS.filter(acc => [ACC_TYPE_STUDENT, ACC_TYPE_MORTGAGE].includes(acc.sub_type))
    const acc_crypto = ACCOUNTS.filter(acc => [ACC_TYPE_CRYPTO].includes(acc.sub_type))
    const acc_assets = ACCOUNTS.filter(acc => [ACC_TYPE_ASSET].includes(acc.sub_type))

    let div, h1, h2, totalFormatted

    for (let accs of [
        [acc_cash, "Cash"],
        [acc_investment, "Investment"],
        [acc_credit, "Credit"],
        [acc_loan, "Loan"],
        [acc_crypto, "Crypto"],
        [acc_assets, "Assets"],
    ]) {
        if (accs[0].length > 0) {
            div = createEl("div", {class: "account-type"})

            let d2 = createEl("div", {class: "account-heading"}) // to change horizontal/vertical mobile/desktop
            h1 = createEl("h2", {}, {marginTop: 0, marginBottom: 0, textAlign: "center"}, accs[1])

            // Note: We also calculate this server side
            let total = 0.
            for (let acc of accs[0]) {
                if (["Credit", "Loan"].includes(accs[1])) {
                    total -= acc.value
                } else {
                    total += acc.value
                }
            }

            // todo: Remove minus sign for cleanness?
            const class_ = total > 0 ? "tran-pos" : "tran-neg"
            totalFormatted = formatAmount(total, 0)
            h2 = createEl("h2", {class: class_}, {marginTop: 0, marginBottom: 0, textAlign: "center"}, totalFormatted) // total todo

            d2.appendChild(h1)
            d2.appendChild(h2)
            div.appendChild(d2)
        }

        for (let acc of accs[0]) {
            div.appendChild(createAccRow(acc, accs[1]))
        }

        if (accs[0].length > 0) {
            section.appendChild(div)
        }
    }

    getEl("nw-span").textContent = TOTALS.net_worth
}

function tranUpdateHelper(id, updated) {
    // Helper function, to reduce code repetition.
    TRANSACTIONS_UPDATED[String(id)] = updated
    TRANSACTIONS = [
        ...TRANSACTIONS.filter(t => t.id !== id),
        updated
    ]
}

function createCatEdit(tran, searchText, id) {
    // Create a select element for categories.
    // todo: Allow creating custom elements here, and search.

    let sel = createCatSel(tran.category, searchText, false, id)

    sel.addEventListener("input", e => {
        let updated = {
            ...tran,
            category: parseInt(e.target.value)
        }
        tranUpdateHelper(tran.id, updated)
    })

    return sel
}

function createCatQuickEdit(tran) {
    let d = createEl("div", {}, {display: "flex", alignItems: "center"})

    let dCatFilter = createEl("div", {id: "div-cat-filter"})

    const selId = "cat-quickedit-search-" + tran.id.toString()
    let catEdit = createCatEdit(tran, QUICK_CAT_SEARCH, selId)
    dCatFilter.appendChild(catEdit) // Auto-save.
    d.appendChild(dCatFilter)

    let h = createEl("h4", {}, {}, "🔎")
    d.appendChild(h)

    let search = createEl("input", {id: "quick-cat-search"}, {width: "70px"},)

    search.addEventListener("input", e => {
        QUICK_CAT_SEARCH = e.target.value
        dCatFilter.replaceChildren() // todo: If not working, getElById.
        dCatFilter.appendChild(createCatEdit(tran, QUICK_CAT_SEARCH, selId)) // Auto-save.

        let updated = {
            ...tran,
            category: parseInt(getEl(selId).value)
        }
        tranUpdateHelper(tran.id, updated)
    })
    d.appendChild(search)

    let btn = createEl("button", {id: "always-btn", class: "button-small"}, {}, "Always")

    if (CAT_ALWAYS) {
        btn.style.border = "2px solid #3cd542"
        btn.style.fontWeight = "bold"
        // btn.style.backroundColor = "#4f6b4d"
    }

    btn.addEventListener("click", _ => {
        CAT_ALWAYS = !CAT_ALWAYS
        refreshTransactions()
    })
    d.appendChild(btn)

    btn =  createEl("button", {class: "button-small"}, {}, "✓")
    btn.addEventListener("click", _ => {
        CAT_QUICKEDIT = false
        saveTransactions()
        refreshTransactions()
    })
    d.appendChild(btn)

    return d
}

function createSplitFormRow(cat, amount, description) {
    let row = createEl("div", {}, {display: "flex"})
    console.log(description, "D")
    let catSel = createCatSel(cat, "", false, "cat-sel-split")
    catSel.id = "split-cat-" + NUM_NEW_SPLITS.toString()

    if (NUM_NEW_SPLITS > 0) {
        description = description + " Split " +  NUM_NEW_SPLITS.toString()
    }

    row.appendChild(catSel)
    let descripIp = createEl(
        "input",
        {
            id: "split-description-" + NUM_NEW_SPLITS.toString(),
            value: description,
        },
        {width: "200px", marginLeft: "20px",}
    )

    row.appendChild(descripIp)

    let amtIp = createEl(
        "input",
        {
            id: "split-amt-" + NUM_NEW_SPLITS.toString(),
            type: "number",
            value: amount,
        },
        {width: "80px", marginLeft: "20px",}
    )

    row.appendChild(amtIp)
    NUM_NEW_SPLITS += 1

    return row
}

function createSplitter(id) {
    SPLIT_TRAN_ID = id

    const tran = TRANSACTIONS.find(t => t.id === id)
    // getEl("split-tran").style.visibility = "visible"
    getEl("split-tran").style.display = "flex"

    let h = getEl("split-tran-title")
    h.textContent = tran.description + ": " + tran.institution_name + ", " + tran.date_display + ", "
    let s = createEl(
        "span",
        {class: "tran-neutral"},
        {fontWeight: "bold"},
            formatAmount(tran.amount,2).replace("-", ""))
    h.appendChild(s)

    let body = getEl("split-tran-body")
    body.replaceChildren()

    const numItems = 2

    for (let splitId=0; splitId<=numItems - 1; splitId++) {
        body.appendChild(createSplitFormRow(tran.category,tran.amount / numItems, tran.description))
    }
}

function createTranRow(tran) {
    // Return a single transaction row.
    const row = createEl("tr", {id: "tran-row-" + tran.id.toString()},{borderBottom: "1px solid #cccccc"} )

    const fontColor = tran.ignored ? IGNORED_COLOR : "black"

    // todo: Don't hard-code 28
    if (tran.highlighted) {
        row.style.backgroundColor = HIGHLIGHT_COLOR
    } else if (tran.category === 28) {
        row.style.backgroundColor = FEE_COLOR
    }

    let col = createEl(
        "td",
        {class: "transaction-cell"},
        // todo: We can only do one or both of this , and descrip flex. We need this to center teh icon,
        // todo and descrip to be horizontal with pending...
        {paddingLeft: "12px", color: "black"}
    ) // Icon

    let d = createEl("div", {}, {display: "flex", alignItems: "center"})

    if (EDIT_MODE_TRAN) {
        d.appendChild(createCatEdit(tran, null))
        col.appendChild(d)

    } else if (tran.id === CAT_QUICKEDIT) {
        col.appendChild(createCatQuickEdit(tran))
    } else {
        // Allow clicking to enter quick edit.
        d.style.cursor = "pointer"
        d.addEventListener("click", _ => {
            CAT_QUICKEDIT = tran.id
            saveTransactions()
            refreshTransactions() // Hopefully-safe recursion.
        })

        if (tran.logo_url.length > 0) {
            let img = createEl("img", {"src": tran.logo_url, alt: "", width: "20px"})
            d.appendChild(img)
        }

        let s
        let iconId = "tran-icon-" + tran.id.toString()
        if (TRANSACTION_ICONS) {
            s = createEl("span", {id: iconId}, {}, catIconFromVal(tran.category))
        } else {
            s = createEl("span", {id: iconId}, {paddingRight: "20px"}, catNameFromVal(tran.category))
        }

        d.appendChild(s)
        col.appendChild(d)
    }

    row.appendChild(col)

    // Flex for pending indicator.
    // col = createEl("td", {class: "transaction-cell"}, {display: "flex"})
    col = createEl("td", {class: "transaction-cell"})

    if (EDIT_MODE_TRAN) {
        let ip = createEl(
            "input",
            {value: tran.description},
            // {width: "200px"},
        )

        ip.addEventListener("input", e => {
            // Re-load from the list as TS maneuver against odd edit pattern
            let tran_ = TRANSACTIONS.find(t => t.id === tran.id)
            let updated = {
                ...tran_,
                description: e.target.value
            }

            tranUpdateHelper(tran.id, updated)
        })

        col.appendChild(ip)
    } else {
        let h = createEl(
            "h4",
            {class: "tran-heading"},
            {fontWeight: "normal", marginLeft: "0px", color: fontColor},
            tran.description
        )

        if (onMobile()) {
            h.style.fontSize = "0.8em"
        }


        if (tran.pending) {
            let text = onMobile() ? "| P" : "| Pending"
            h.appendChild(createEl(
                "span",
                {class: "tran-heading"},
                {color: "#999999", fontWeight: "normal", marginLeft: "8px"},
                text)
            )
        }
        col.appendChild(h)
    }
    row.appendChild(col)

    // Institution name: Hide on mobile.
    col = createEl("td", {class: "transaction-cell"}, {display: "flex"})
    if (!onMobile()) {
        if (EDIT_MODE_TRAN) {
            let ip = createEl(
                "input",
                {value: tran.institution_name},
            )

            ip.addEventListener("input", e => {
                // Re-load from the list as TS maneuver against odd edit pattern
                let tran_ = TRANSACTIONS.find(t => t.id === tran.id)
                let updated = {
                    ...tran_,
                    institution_name: e.target.value
                }
                tranUpdateHelper(tran.id, updated)
            })

            col.appendChild(ip)
        } else {
            let h = createEl(
                "h4",
                {class: "tran-heading"},
                {fontWeight: "normal", marginLeft: "0px", color: fontColor},
                tran.institution_name,
            )
            col.appendChild(h)
        }
    } else {
        getEl("institution-col").textContent = ""  // Blank the column name
    }
    row.appendChild(col)

    col = createEl("td", {class: "transaction-cell"}, {})
    let h
    if (EDIT_MODE_TRAN) {
        h = createEl("input", {value: tran.notes}, {marginRight: "30px"})

        h.addEventListener("input", e => {
            // Re-load from the list as TS maneuver against odd edit pattern
            let tran_ = TRANSACTIONS.find(t => t.id === tran.id)
            let updated = {
                ...tran_,
                notes: e.target.value
            }
            tranUpdateHelper(tran.id, updated)
        })
    } else {
        h = createEl(
            "h4",
            {class: "tran-heading"},
            {fontWeight: "normal", color: "#444444", marginRight: "60px"},
            tran.notes
        )
    }

    col.appendChild(h)
    row.appendChild(col)

    col = createEl("td", {class: "transaction-cell"})
    if (EDIT_MODE_TRAN) {
        h = createEl(
            "input",
            { value: tran.amount},
            {width: "80px", marginRight: "30px"},
        )

        h.addEventListener("input", e => {
            if (isValidNumber(e.target.value)) {
                // Re-load from the list as TS maneuver against odd edit pattern
                let tran_ = TRANSACTIONS.find(t => t.id === tran.id)
                let updated = {
                    ...tran_,
                    amount: parseFloat(e.target.value)
                }
                tranUpdateHelper(tran.id, updated)
            }
        })

    } else {
        let tranClass = tran.amount > 0. ? "tran-pos" : "tran-neutral"
        let amtDecimals = Math.abs(tran.amount) < 100

        let amtText = formatAmount(tran.amount, amtDecimals)
        if (tran.amount > 0.) {
            amtText = "+" + amtText
        } else {
            amtText = amtText.replace("-", "")
        }

        h = createEl("h4",
            {class: "tran-heading " + tranClass},
            {
                textAlign: "right",
                marginRight: "40px",
                color: Math.abs(tran.amount) > THRESH_HIGH_AMOUNT ? COLOR_HIGH_AMOUNT : null,
            }, amtText
        )
        if  (tran.ignored) {
            h.style.color = IGNORED_COLOR
        }
    }

    col.appendChild(h)
    row.appendChild(col)

    col = createEl("td", {class: "transaction-cell"})
    if (EDIT_MODE_TRAN) {
        d = createEl("div", {}, {display: "flex"})
        let h = createEl("input", {type: "date", value: tran.date}, {width: "120px"})

        h.addEventListener("input", e => {
            // Re-load from the list as TS maneuver against odd edit pattern
            let tran_ = TRANSACTIONS.find(t => t.id === tran.id)
            let updated = {
                ...tran_,
                date: e.target.value
            }
            tranUpdateHelper(tran.id, updated)
        })

        let delBtn = createEl("button", {class: "button-small"}, {cursor: "pointer"}, "❌")
        delBtn.addEventListener("click", _ => {
            const data = {ids: [tran.id]}
            fetch("/delete-transactions", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {
                    if (!r.success) {
                        console.error("Error deleting this transactcion: ", tran)
                    }
                });
            let row = getEl("tran-row-" + tran.id.toString())
            row.remove()

            TRANSACTIONS = TRANSACTIONS.filter(t => t.id !== tran.id)
        })

        let ignoreBtn = createEl("button", {class: "button-small"}, {cursor: "pointer"}, "Ignore")
        ignoreBtn.addEventListener("click", _ => {
            fetch("/toggle-ignore", {body: JSON.stringify({id: tran.id}), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {
                });
            TRANSACTIONS = [
                ...TRANSACTIONS.filter(t => t.id !== tran.id),
                {
                    ...tran,
                    ignored: !tran.ignored
                }
            ]

            if (!tran.ignored) {
                ignoreBtn.style.borderColor = "#41c541"
                ignoreBtn.style.fontWeight = "bold"
            } else {
                ignoreBtn.style.borderColor = null
                ignoreBtn.style.fontWeight = null
            }

            // todo: Refresh spending highlights; it will hav echanged.
        })
        if (tran.ignored) {
            ignoreBtn.style.borderColor = "#41c541"
            ignoreBtn.style.fontWeight = "bold"
        }

        d.appendChild(h)
        d.appendChild(ignoreBtn)
        d.appendChild(delBtn)
        col.appendChild(d)
    } else {
        let h = createEl("h4", {class: "tran-heading"}, {color: fontColor}, tran.date_display)
        col.appendChild(h)
    }

    row.appendChild(col)

    // mobile?
    col = createEl("td", {class: "transaction-cell"})


    if (!onMobile()) {
        // Highlighter icon.
        let s = createEl("span", {}, {marginLeft: "6px", marginRight: 0, cursor: "pointer"}, "🖍️")

        s.addEventListener("click", _ => {
            fetch("/toggle-highlight", {body: JSON.stringify({id: tran.id}), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {});

            tran.highlighted = !tran.highlighted
            let bgColor = tran.highlighted ? HIGHLIGHT_COLOR : "white"
            getEl("tran-row-" + tran.id.toString()).style.backgroundColor = bgColor
        })

        col.appendChild(s)
    }

    // Split button
    // Pending transactions are likely to be modified by the institution; splitting them will cause unexpected behavior.
    if (!tran.pending) {
        let s = createEl("span", {}, {marginLeft: "6px", marginRight: 0, cursor: "pointer"}, "↔️")

        s.addEventListener("click", _ => {
            createSplitter(tran.id)
        })

        col.appendChild(s)
    }

    row.appendChild(col)
    return row
}

function refreshTransactions() {
    // todo: Try to reduce calls to this function as much as possible, eg when only editing one row or column in a row.
    //[Re]populate the transactions table based on state.
    console.log("Refreshing transactions...")
    QUICK_CAT_SEARCH = ""

    let transactions = filterTransactions()

    let tbody = getEl("transaction-tbody")
    tbody.replaceChildren();

    for (let tran of transactions) {
        const row = createTranRow(tran)
        tbody.appendChild(row)
    }
}

function updateTranFilter() {
    TRANSACTIONS_LOADED = false // Allows more transactions to be loaded from the server.

    SEARCH_TEXT = getEl("search").value.toLowerCase()

    // todo: Enforce integer value.
    let valueThresh = getEl("transaction-value-filter").value
    // Remove non-integer values

    // todo: number field here is actually interfering, returning an empty string if invalid;
    // so, we can't just ignore chars.

    VALUE_THRESH = parseInt(valueThresh.replace(/\D+/g, ''))

    FILTER_START = getEl("tran-filter-start").value
    FILTER_END = getEl("tran-filter-end").value
    refreshTransactions()
}


function addAccountManual() {
    // We use this when submitting a new manual account

    // getEl("add-account-manaul").addEventListener("click", _ => {
    //                 <input id="add-manual-name" />
    //
    //                 <select id="add-manual-type" style="border: 1px solid black; height: 32px; width: 156px;">
    //
    //                 <input id="add-manual-current" type="number" value="0" />

    // todo: Validate no blank account name
    const subType = parseInt(getEl("add-manual-type").value)

    const data = {
        name: getEl("add-manual-name").value,
        sub_type: subType,
        current: parseFloat(getEl("add-manual-current").value),
        iso_currency_code: getEl("add-manual-currency-code").value,
    }

    if (subType === SUB_TYPE_CRYPTO) {
        data.current = parseFloat(getEl("add-manual-asset-quantity").value)
        data.iso_currency_code = parseInt(getEl("add-manual-asset-type").value)
    }

    fetch("/add-account-manual", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
        .then(result => result.json())
        .then(r => {
            console.log(r)
            // todo: Handle a failure.
            // Add the account with info from the server; this will have the server-assigned database ID.
            ACCOUNTS.push(r.account)
            refreshAccounts()
        });

    toggleAddManual()
}

function setupEditTranButton() {
    let btn = getEl("edit-transactions");

    btn.addEventListener("click", _ => {
        if (EDIT_MODE_TRAN) {
            // Update transactions in place, so a refresh isn't required.
            for (let tran of Object.values(TRANSACTIONS_UPDATED)) {
                let date = new Date(tran.date)
                tran.date_display = (date.getUTCMonth() + 1) % 12 + "/" + date.getUTCDate()

                // todo: To update categories in place, we will need to parse categories in the UI instead of using
                // todo teh passed cats from the backend.

                TRANSACTIONS = [
                    ...TRANSACTIONS.filter(t => t.id !== tran.id),
                    tran,
                ]
            }

            EDIT_MODE_TRAN = false
            btn.textContent = "✎ Edit"
            saveTransactions()
        } else {
            // Enable editing on click.
            EDIT_MODE_TRAN = true
            btn.textContent = "Save transactions"
        }
        refreshTransactions()
    })
}

function saveTransactions() {
    const data = {
        // Discard keys; we mainly use them for updating internally here.
        transactions: Object.values(TRANSACTIONS_UPDATED),
        create_rule: CAT_ALWAYS,
    }

    console.log("Tran edit data: ", data)

    // Save transactions to the database.
    fetch("/edit-transactions", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            if (!r.success) {
                console.error("Transaction save failed")
            }
        });

    TRANSACTIONS_UPDATED = {}
}

function setupAccEditForm(id) {
    let acc = ACCOUNTS.filter(a => a.id === id)[0]

    // Setup the form for adding and editing accounts.
    let outerDiv = getEl("account-div")
    // outerDiv.style.visibility = "visible"
    outerDiv.style.display = "flex"
    let form = getEl("account-form")
    form.replaceChildren()

    let d, h, ip

    d = createEl("div", {}, {textAlign: "center"})
    h = createEl("h2", {}, {marginTop: 0, marginBottom: "18px"}, "Edit an account")
    d.appendChild(h)
    form.appendChild(d)

    d = createEl("div", {}, {textAlign: "center"})
    let officialText = acc.institution

    if (!acc.manual) {
        officialText += ": " + acc.name
    }

    if (!acc.manual && acc.name_official) {
        officialText += ", " + acc.name_official
    }

    h = createEl("h3", {}, {margin: 0}, officialText)
    d.appendChild(h)
    form.appendChild(d)

    d = createEl("div", {}, {textAlign: "center"})
    h = createEl("h3", {}, {marginTop: "8px", marginBottom: "40px"}, "Type: " + accTypeFromNum(acc.sub_type))
    d.appendChild(h)
    form.appendChild(d)

    if (acc.needs_attention) {
        let attentionBtn = createEl(
            "button",
            {class: "button-general", type: "button"},
            {marginBottom: "40px", backgroundColor: "#eccfec"},
            "⚠️ This account needs your attention. Click here to repair it."
        )
        attentionBtn.addEventListener("click", _ => {
            data = { id: acc.id}
            fetch("/create-link-token-update", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    console.log("Acc update response:", r)
                    LINK_TOKEN = r.link_token
                    getPublicToken()
                });
        })
        form.appendChild(attentionBtn)
    }

    d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})

    if (acc.manual) {
        h = createEl("h3", {}, {marginBottom: 0, marginTop: "18px"}, "Account name")
        ip = createEl("input", {value: acc.name})
        ip.addEventListener("input", e => {
            let acc_ = ACCOUNTS.find(t => t.id === acc.id)
            let updated = {
                ...acc_,
                name: e.target.value
            }
            ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
            ACCOUNTS_UPDATED[acc.id] = updated
            refreshAccounts()
        })
    } else {
        h = createEl("h3", {}, {marginTop: 0, marginBottom: "18px"}, "Nickname")
        ip = createEl("input", {value: acc.nickname})
        ip.addEventListener("input", e => {
            let acc_ = ACCOUNTS.find(t => t.id === acc.id)
            let updated = {
                ...acc_,
                nickname: e.target.value
            }
            ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
            ACCOUNTS_UPDATED[acc.id] = updated
            refreshAccounts()
        })
    }

    d.appendChild(h)
    d.appendChild(ip)
    form.appendChild(d)

// todo: Allow editing account type.

    // <div style="display: flex; align-items: center; justify-content: space-between;">
    //     <h3>Type</h3>
    //     {#                    todo: DRY #}
    //     <select id="add-manual-type" style="border: 1px solid black; height: 32px; width: 156px;">
    //         <option value="0">Checking</option>
    //         <option value="1">Savings</option>
    //         <option value="2">Debit card</option>
    //         <option value="3">Credit card</option>
    //         <option value="4">401K</option>
    //         <option value="5">Student</option>
    //         <option value="6">Mortgage</option>
    //         <option value="7">CD</option>
    //         <option value="8">Money market</option>
    //         <option value="9">IRA</option>
    //         <option value="10">Mutual fund</option>
    //         <option value="11">Crypto</option>
    //         <option value="12">Asset (misc)</option>
    //         <option value="13">Brokerage</option>
    //         <option value="14">Roth</option>
    //     </select>
    // </div>


    if (acc.manual) {
        d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})

        if (acc.sub_type === SUB_TYPE_CRYPTO) {
            h = createEl("h3", {}, {marginBottom: 0, marginTop: "18px"}, "Crypto asset")
            ip = createEl("select", {}, {height: "40px"})

            Bitcoin = 0
            Ethereum = 1
            Bnb = 2
            Solana = 3
            Xrp = 4
            // todo: Set this up elsewhere. From `asset_prices.py`
            for (let crypto of [
                [0, "Bitcoin"],
                [1, "Ethereum"],
                [2, "BNB"],
                [3, "Solana"],
                [4, "XRP"],
            ]) {
                let opt = createEl("option", {value: crypto[0]}, {}, crypto[1])
                if (acc.asset_type === crypto[0]) {
                    opt.setAttribute("selected", true)
                }
                ip.appendChild(opt)
            }
            // todo: DRY
            ip.addEventListener("input", e => {
                let acc_ = ACCOUNTS.find(t => t.id === acc.id)
                let updated = {
                    ...acc_,
                    asset_type: parseInt(e.target.value),
                }
                ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
                ACCOUNTS_UPDATED[acc.id] = updated
                refreshAccounts()
            })
        } else {
            h = createEl("h3", {}, {marginBottom: 0, marginTop: "18px"}, "Currency code")
            ip = createEl("input", {value: acc.iso_currency_code, maxLength: "3"})

            // todo: DRY
            ip.addEventListener("input", e => {
                let acc_ = ACCOUNTS.find(t => t.id === acc.id)
                let updated = {
                    ...acc_,
                    iso_currency_code: e.target.value,
                }
                ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
                ACCOUNTS_UPDATED[acc.id] = updated
                refreshAccounts()
            })
        }

        d.appendChild(h)
        d.appendChild(ip)

        form.appendChild(d)

        d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})

        if (acc.sub_type === SUB_TYPE_CRYPTO) {
            h = createEl("h3", {}, {marginBottom: 0}, "Quantity (number of coins)")
            ip = createEl("input", {type: "number", value: acc.asset_quantity})

            // todo: DRY
            ip.addEventListener("input", e => {
                let acc_ = ACCOUNTS.find(t => t.id === acc.id)
                let updated = {
                    ...acc_,
                    asset_quantity: parseFloat(e.target.value),
                }
                ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
                ACCOUNTS_UPDATED[acc.id] = updated
                refreshAccounts()
            })
        } else {
            h = createEl("h3", {}, {marginBottom: 0}, "Value")
            ip = createEl("input", {type: "number", value: acc.value})

            // todo: DRY
            ip.addEventListener("input", e => {
                // Re-load from the list as TS maneuver against odd edit pattern
                let acc_ = ACCOUNTS.find(t => t.id === acc.id)
                let updated = {
                    ...acc_,
                    current:parseFloat(e.target.value),
                }
                ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== acc.id), updated]
                ACCOUNTS_UPDATED[acc.id] = updated
                refreshAccounts()
            })
        }


        d.appendChild(h)
        d.appendChild(ip)
        form.appendChild(d)
    }

    d = createEl("div", {}, {display: "flex", justifyContent: "center", marginTop: "18px"})
    let btnSave = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "💾 Save")
    let btnCancel = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "Cancel")

    let btnDelete = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "❌ Delete")
    if (!acc.manual) {
        btnDelete.textContent = "🔗Unlink"
    }

    btnSave.addEventListener("click", _ => {
        const data = {
            // Discard keys; we mainly use them for updating internally here.
            accounts: Object.values(ACCOUNTS_UPDATED)
        }

        fetch("/edit-accounts", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
            .then(result => result.json())
            .then(r => {
                if (!r.success) {
                    console.error("Account edits save failed")
                }
            });

        // Update the ACCOUNTS list, and refresh accounts.
        for (let updated of Object.values(ACCOUNTS_UPDATED)) {
            ACCOUNTS = [...ACCOUNTS.filter(a => a.id !== updated.id), updated]
        }
        refreshAccounts()
        ACCOUNTS_UPDATED = {}
        // Update our accoutns list, and refresh.

        outerDiv.style.display = "none"
    })

    btnCancel.addEventListener("click", _ => {
        ACCOUNTS_UPDATED = {}
        outerDiv.style.display = "none"
    })

    // todo: Confirmation.
    btnDelete.addEventListener("click", _ => {
        let data = {ids: [acc.id]}
        fetch("/delete-accounts", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
            .then(result => result.json())
            .then(r => {
                if (!r.success) {
                    console.error("Account edits delete failed")
                }
            });
        ACCOUNTS = ACCOUNTS.filter(a => a.id !== acc.id)
        refreshAccounts()
        // outerDiv.style.visibility = "collapse"
        outerDiv.style.display = "none"
    })

    d.appendChild(btnSave)
    d.appendChild(btnCancel)
    d.appendChild(btnDelete)
    form.appendChild(d)
}

function setupSpendingHighlights() {
    // Consider a template for this instead; it should be faster.
    let biggestCats  = getEl("biggest-cats")
    biggestCats.replaceChildren()

    let h, text

    h = createEl(
        "h3",
        {class: "spending-highlight-title"},
        {},
        "Total: "
    )

    let s = createEl("span", {class: "tran-neutral"}, {}, formatAmount(SPENDING_HIGHLIGHTS.total, 0).replace("-", ""))
    h.appendChild(s)
    biggestCats.appendChild(h)

    for (let highlight of SPENDING_HIGHLIGHTS.by_cat.slice(0, HIGHLIGHTS_SIZE)) {
        text = catDisp(highlight[0]) + ": "
        h = createEl(
            "h4",
            {},
            {marginBottom: 0, marginTop: 0, cursor: "pointer", fontWeight: "normal"},
            text
        )

        let amountText = formatAmount(highlight[1][1], 0).replace("-", "")
        let s = createEl("span", {class: "tran-neutral"}, {fontWeight: "bold"}, amountText)

        // Terser text on mobile.
        let s2Text
        if (onMobile()) {
            s2Text = " (" + highlight[1][0] + ")"
        } else {
            s2Text = " in " + highlight[1][0] + " transactions"
        }
        let s2 = createEl("span", {}, {}, s2Text)

        h.appendChild(s)
        h.appendChild(s2)

        h.addEventListener("click", _ => {
            CURRENT_PAGE = 0
            FILTER_CAT = highlight[0]
            getEl("tran-filter-sel").value = highlight[0].toString()
            updateTranFilter()
        })

        biggestCats.appendChild(h)
    }

    let changes = getEl("biggest-changes")
    changes.replaceChildren()

    h = createEl("h3", {class: "spending-highlight-title"}, {}, "Changes. Total: ")
    let changeTotal = formatAmount(SPENDING_HIGHLIGHTS.total_change, 0)
    if (SPENDING_HIGHLIGHTS.total_change > 0) {
        changeTotal = "+" + changeTotal
    }
    s = createEl("span", {class: "tran-neutral"}, {}, changeTotal)
    //
    // h = createEl(
    //     "h3",
    //     {},
    //     {marginRight: "40px"},
    //     "Changes. Total: "
    // )

    h.appendChild(s)
    biggestCats.appendChild(h)
    changes.appendChild(h)

    for (let catChange of SPENDING_HIGHLIGHTS.cat_changes.slice(0, HIGHLIGHTS_SIZE)) {

        // todo: + sign explicitly if spending went up.
        h = createEl(
            "h4",
            {},
            {fontWeight: "normal", cursor: "pointer", marginTop: 0, marginBottom: 0},
            catDisp(catChange[0]) + ": "
        )

        let changeText = formatAmount(catChange[1], 0)
        if (catChange[1] > 0) {
            changeText = "+" + changeText
        }
        let s = createEl("span", {class: "tran-neutral"}, {fontWeight: "bold"}, changeText)
        h.appendChild(s)

        h.addEventListener("click", _ => {
            CURRENT_PAGE = 0
            FILTER_CAT = catChange[0]
            getEl("tran-filter-sel").value = catChange[0].toString()
            updateTranFilter()
        })

        changes.appendChild(h)
    }

    let largePurchases  = getEl("large-purchases")
    // largePurchases.replaceChildren()

    if (SPENDING_HIGHLIGHTS.large_purchases.length === 0) {
        h = createEl(
            "h4",
            {},
            // {marginRight: "40px", cursor: "pointer"},
            // {marginRight: "40px", fontWeight: "normal"},
            {fontWeight: "normal"},
            "(None)"
        )
        largePurchases.appendChild(h)
    }

    for (let purchase of SPENDING_HIGHLIGHTS.large_purchases.slice(0, HIGHLIGHTS_SIZE)) {
        text = purchase.description + ": "
        h = createEl(
            "h4",
            {},
            // {marginRight: "40px", cursor: "pointer"},
            // {marginRight: "40px", fontWeight: "normal", marginTop: 0, marginBottom: 0},
            {fontWeight: "normal", marginTop: 0, marginBottom: 0},
            text
        )
        let s = createEl(
            "span",
            {class: "tran-neutral"},
            {fontWeight: "bold"},
            formatAmount(purchase.amount, 0).replace("-", "")
        )
        // let s2 = createEl("span", {}, {}, " in " + purchase[1][0] + " transactions")

        h.appendChild(s)

        // h.addEventListener("click", _ => {
        //     CURRENT_PAGE = 0
        //     FILTER_CAT = purchase[0]
        //     getEl("tran-filter-sel").value = purchase[0].toString()
        //     updateTranFilter()
        // })

        largePurchases.appendChild(h)
    }
}

function setupCatFilter(searchText) {
    // Set up the main transaction category filter. Done in JS for consistency with other CAT filters.
    let div = getEl("tran-cat-filter")
    let sel = createCatSel(-2, "", true, "tran-filter-sel")

    sel.addEventListener("input", e => {
        FILTER_CAT = parseInt(e.target.value)
        TRANSACTIONS_LOADED = false
        refreshTransactions()
    })

    div.appendChild(sel)
}

function init() {
    // We run this on page load
    getEl("link-button").addEventListener("click", _ => {
        fetch("/create-link-token", FETCH_HEADERS_GET)
            // Parse JSON if able.
            .then(result => result.json())
            .then(r => {
                LINK_TOKEN = r.link_token
                getPublicToken()
            });
    });

    refreshAccounts()
    refreshTransactions()

    let check = getEl("icon-checkbox")
    check.addEventListener("click", _ => {
        TRANSACTION_ICONS = !TRANSACTION_ICONS

        if (EDIT_MODE_TRAN) {
            return
        }

        for (let tran of TRANSACTIONS) {
            let el= getEl("tran-icon-" + tran.id.toString())
            // We won't find the icon if we've loaded more than is on the page.
            if (el === null) {
                continue
            }

            if (CAT_QUICKEDIT === tran.id) {
                continue
            }

            let iconText
            if (TRANSACTION_ICONS) {
                iconText = catIconFromVal(tran.category)
                el.style.paddingRight = "0"
            } else {
                iconText = catNameFromVal(tran.category)
                el.style.paddingRight = "20px"
            }
            el.textContent = iconText

        }
    })

    setupEditTranButton()

    // Put this back; currently removed due due to layout shifts.
    // let refreshIndicator = getEl("refreshing-indicator")
    // refreshIndicator.style.visibility = "visible"

    // Tell the backend to start updating account data values etc, and receive updates based on that here.
    fetch("/post-dash-load", FETCH_HEADERS_GET)
        // Parse JSON if able.
        .then(result => result.json())
        .then(r => {
            TOTALS = r.totals

            // refreshIndicator.style.visibility = "collapse" // todo A/R
            // todo: Loading/spinning indicator on screen until the update is complete.
            for (let acc_new of r.sub_accs) {
                ACCOUNTS = [
                    ...ACCOUNTS.filter(a => a.id !== acc_new.id),
                    acc_new
                ]
            }

            for (let tran_new of r.transactions) {
                TRANSACTIONS = [
                    ...TRANSACTIONS.filter(a => a.id !== tran_new.id),
                    tran_new
                ]
            }
            if (r.sub_accs.length > 0 || r.acc_health.length > 0) {
                ACC_HEALTH = r.acc_health
                refreshAccounts()
            }
            if (r.transactions.length > 0) {
                refreshTransactions()
                // todo: This won't work until you also update spending highlights.
                setupSpendingHighlights()
            }
        });

    setupSpendingHighlights()
    setupCatFilter()

    if (onMobile()) {
        // Delete " acccount" on these buttons, to save space.
        getEl("link-button").textContent = "➕ Syncing"
        getEl("add-manual-button").textContent = "➕ Manual"

        // getEl("biggest-change-h").textContent = "Changes:"
        // getEl("large-purchases-h").textContent = "Large:"
    } else {
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                CAT_QUICKEDIT = null
                CAT_ALWAYS = false
                refreshTransactions() // todo: Don't refresh all. just the text edit in question.
            }
        });
    }
}

init()

function addTranManual() {
    // Add a transaction, eg from clicking the Add button
    // We use this temporary ID to keep track of this transaction until it's assigned a real one by the server.
    // const tempId = parseInt(Math.random() * 10_000)

    // Ensure the name is unique, or the DB will refuse to save it due to a unique_together constraint.

    // todo: This will fail if you hit 10; Fix this.
    let highestNum = 0
    for (let tran of TRANSACTIONS) {
        if (tran.description.includes("New transaction")) {
            let number = parseInt(tran.description.charAt(tran.description.length - 1))
            if ( !Number.isNaN(number) && number > highestNum) {
                highestNum = number
            }
        }
    }
    let tran_name = "New transaction " + (highestNum + 1).toString()

    const newTran =  {
        amount: 0.,
        amount_class: "tran-neutral",
        category: -1,
        date: new Date().toISOString().split('T')[0],
        date_display: "03/11",
        description: tran_name,
        id: -999,
        logo_url: "",
        notes: "",
        currency_code: "USD",
        institution_name: "",
        pending: false
    }

    const payload = {transactions: [newTran]}

    fetch("/add-transactions", { body: JSON.stringify(payload), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            // // We could just hold off on adding the transaction to the UI, but I think this approach
            // // will feel more responsive due to showing the tran immediately.
            // TRANSACTIONS = TRANSACTIONS.filter(t => t.id !== tempId0)

            if (r.success) {
                newTran.id = r.ids[0]
                TRANSACTIONS.push(newTran)

                // todo: For a snapier response, consider adding immediatley, and retroactively changing its id.
                const row = createTranRow(newTran)
                getEl("transaction-tbody").prepend(row)
            } else {
                console.error("Problem adding this transaction")
                // (We've just removed it from the state above)
            }
        });
}

function toggleAddManual() {
    let form = getEl("add-manual-form")
    let btnToggle = getEl("add-manual-button")

    // if (form.style.visibility === "visible") {
    if (form.style.display === "flex") {
        // form.style.visibility = "collapse"
        form.style.display = "none"
        // btnToggle.textContent = "➕ Manual account"
        // btnToggle.style.visibility = "visible"
        btnToggle.style.display = "flex"
    } else {
        // form.style.visibility = "visible"
        form.style.display = "flex"
        // btnToggle.style.visibility = "hidden"
        btnToggle.style.display = "none"
    }
}

function changePage(direction) {
    CURRENT_PAGE += direction // eg-1 or 1

    if (CURRENT_PAGE < 0) {
        CURRENT_PAGE = 0
    }

    TRANSACTIONS_LOADED = false // Allows more transactions to be loaded from the server.
    refreshTransactions()
}

function saveSplit() {
    // We use the existing add and modify APIs, vice a special one.
    let tranParent = TRANSACTIONS.find(t => t.id === SPLIT_TRAN_ID)
    tranParent.amount = parseInt(getEl("split-amt-0").value)
    tranParent.category = parseInt(getEl("split-cat-0").value)
    tranParent.description = getEl("split-description-0").value

    TRANSACTIONS = [...TRANSACTIONS.filter(t => t.id !== tranParent.id), tranParent]
    refreshTransactions() // todo: Not ideal, vice a ninja update, as below.

    // Modify the parent as required.
    const payloadModify = {
        transactions: [tranParent],
        create_rule: false,
    }

    // Save transactions to the database.
    fetch("/edit-transactions", { body: JSON.stringify(payloadModify), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            if (!r.success) {
                console.error("Transaction split (edit component) failed")
            }
        });


    let payloadAdd = {transactions: []}
    for (let i= 1; i < NUM_NEW_SPLITS; i++) {
        payloadAdd.transactions.push({
            ...tranParent,
            description: getEl("split-description-" + i.toString()).value,
            amount: parseInt(getEl("split-amt-" + i.toString()).value),
            category: parseInt(getEl("split-cat-" + i.toString()).value),
        })
    }

    // Add additional transactions.
    fetch("/add-transactions", { body: JSON.stringify(payloadAdd), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            if (r.success) {
                for (let newTran of payloadAdd.transactions) {
                    TRANSACTIONS.push({
                        ...newTran,
                        id: r.ids[0],
                    })

                    // todo: For a snapier response, consider adding immediatley, and retroactively changing its id.
                    const row = createTranRow(newTran)
                    getEl("transaction-tbody").prepend(row)
                }
            } else {
                console.error("Problem adding this new split transaction.")
            }
        });

    // getEl("split-tran").style.visibility = "collapse"
    getEl("split-tran").style.display = "none"
    SPLIT_TRAN_ID = null
    NUM_NEW_SPLITS = 0
}

function hideSplit() {
    // Hide teh split section.
    // getEl("split-tran").style.visibility = "collapse"
    getEl("split-tran").style.display = "none"
    SPLIT_TRAN_ID = null
    NUM_NEW_SPLITS = 0
}

function addSplitTran() {
    // Add a row to the split tran form.

    let body = getEl("split-tran-body")
    const tran = TRANSACTIONS.find(t => t.id === SPLIT_TRAN_ID)

    body.appendChild(createSplitFormRow(tran.category, 0., tran.description))
}

function changeDates(start, end) {
    // Used, eg by the month quickpick buttons, to change the dates.
    getEl("tran-filter-start").value = start
    getEl("tran-filter-end").value = end

    updateTranFilter()

    refreshTransactions()
}

function handleAccountType() {
    // For updating the template-based account add, for crypto and other assets vice manual value.
    if (parseInt(getEl("add-manual-type").value) === SUB_TYPE_CRYPTO) {

        getEl("non-asset-form-items").style.display = "none"
        getEl("asset-form-items").style.display = "block"
    } else {
        getEl("non-asset-form-items").style.display = "block"
        getEl("asset-form-items").style.display = "none"
    }

}
