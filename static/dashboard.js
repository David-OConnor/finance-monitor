// Global mutal variables
let LINK_TOKEN = ""
let SEARCH_TEXT = ""
let FILTER_START = "1999-09-09"  // todo!
let FILTER_END = "2040-09-09"  // todo!
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


// todo: Config object?

// Includes all loaded transactions
// let TRANSACTIONS = [] // Loaded from template initially
// let ACCOUNTS = [] // Loaded from temp templatme initially.

// let TRANSACTIONS_DISPLAYED = []
let TRANSACTION_ICONS = true
let EDIT_MODE_TRAN = false
let EDIT_MODE_ACC = false

// We use an object vice map for serialization compatibility.
let TRANSACTIONS_UPDATED = {}
let ACCOUNTS_UPDATED = {}

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

    console.log("Getting public token. Link token: ", LINK_TOKEN)
    let handler = Plaid.create({
        // Create a new link_token to initialize Link
        // token: await fetch("/create_link_token", {...FETCH_HEADERS_POST }).link_token,
        token: LINK_TOKEN,
        onLoad: function() {
            console.log("Link loaded")
            // Optional, called when Link loads
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
            console.log("Received a public token; sending to the backend.")
            console.log("Metadata: ", metadata)

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
            console.log("Link flow exited")
            // The user exited the Link flow.
            if (err != null) {
                // The user encountered a Plaid API error prior to exiting.
            }
            // metadata contains information about the institution
            // that the user selected and the most recent API request IDs.
            // Storing this information can be helpful for support.
        },
        onEvent: function(eventName, metadata) {
            console.log("Link flow event: ", eventName)
            console.log("Metadata: ", metadata)
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
    if (FILTER_CAT !== null && FILTER_CAT != -2) {
        transactions = transactions.filter(t => t.categories.includes(FILTER_CAT))
    }

    // Note: This truthy statement catches both an empty string, and an undefined we get on init.
    if (searchText) {
        transactions = transactions.filter(t => {
            return t.description.toLowerCase().includes(searchText) ||
                t.notes.toLowerCase().includes(searchText) ||
                t.categories_text.join().toLowerCase().includes(searchText)
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
    // todo: Kludge for sometimes not loading enough. Fix this.
    // const endI = CURRENT_PAGE * PAGE_SIZE + 2*PAGE_SIZE

    transactions = transactions.slice(startI, endI)

    if (!TRANSACTIONS_LOADED) {  // A check against doing this multiple times (or finititely) in a row.
        console.log("Trans not loaded")
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
                        refreshTransactions()
                    }
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

    let h_a = createEl("h4", {class: "acct-hdg"}, {marginRight: "26px"}, name)

    let val = acc.current
    if (["Credit", "Loan"].includes(type)) {
        val *= -1
    }
    // todo: Negate Acc if
    const valClass = val > 0 ? "tran_pos" : "tran_neg"

    // Format with a comma, and no decimal places
    const valueFormatted = formatAmount(val, false)
    let h_b = createEl("h4", {class: "acct-hdg " + valClass}, {}, valueFormatted)

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
        ACC_TYPE_BROKERAGE, ACC_TYPE_ROTH].includes(acc.sub_type))

    const acc_credit = ACCOUNTS.filter(acc => [ACC_TYPE_CREDIT, ACC_TYPE_DEBIT].includes(acc.sub_type))
    const acc_loan = ACCOUNTS.filter(acc => [ACC_TYPE_STUDENT, ACC_TYPE_MORTGAGE].includes(acc.sub_type))
    const acc_crypto = ACCOUNTS.filter(acc => [ACC_TYPE_CRYPTO].includes(acc.sub_type))
    const acc_assets = ACCOUNTS.filter(acc => [ACC_TYPE_ASSET].includes(acc.sub_type))

    let div, h1, h2, class_, totalFormatted

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

            // note: We also calcualte this server side
            let total = 0.
            for (let acc of accs[0]) {
                if (["Credit", "Loan"].includes(accs[1])) {
                    total -= acc.current
                } else {
                    total += acc.current
                }
            }

            // todo: Remove minus sign for cleanness?
            const class_ = total > 0 ? "tran_pos" : "tran_neg"
            totalFormatted = formatAmount(total, false)
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
}

function createCatEdit(tran, autoSave, searchText) {
    // Create a select element for categories.
    // todo: Allow creating custom elements here, and search.
    let sel = createEl("select", {}, {})

    let opt
    for (let cat of catNames) {
        if (searchText) {
            console.log("Search text")
        }

        let catPrimary = tran.categories.length > 0 ? tran.categories[0] : -1  // -1 is uncategorized

        opt = createEl("option", {value: cat[0]}, {}, cat[1])
        if (cat[0] === catPrimary) {
            opt.setAttribute("selected", "")
        }

        sel.appendChild(opt)

        sel.addEventListener("input", e => {
            let updated = {
                ...tran,
                categories: [parseInt(e.target.value)]
            }
            // todo: DRY!
            TRANSACTIONS_UPDATED[String(tran.id)] = updated

            if (autoSave) {
                // todo: DRY with setup tran edit button, although with some differences, like
                // nulling quick edit, and refreshing transactions.

                const data = {
                    // Discard keys; we mainly use them for updating internally here.
                    transactions: Object.values(TRANSACTIONS_UPDATED),
                    create_rule: CAT_ALWAYS,
                }

                // Save transactions to the database.
                fetch("/edit-transactions", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
                    .then(result => result.json())
                    .then(r => {
                        if (!r.success) {
                            // console.error("Transaction save failed")
                        } else {
                            // window.location.reload(); // todo temp until we can update cat in place.
                        }
                    });

                // todo: Like in many cases, you're getting some sort of unpleasant, but not fatal recusion. Why?
                // todo: And, only edit the specific icon div you're changing... Don't run refreshTransactions at all!
                TRANSACTIONS = [
                    ...TRANSACTIONS.filter(t => t.id !== tran.id),
                    updated
                ]
                CAT_QUICKEDIT = null
                CAT_ALWAYS = false
                refreshTransactions()
            }
        })
    }

    return sel
}

function createTranRow(tran) {
    // Return a single transaction row.
    const row = createEl("tr", {id: "tran-row-" + tran.id.toString()},{borderBottom: "1px solid #cccccc"} )

    // todo: Don't hard-code 28
    if (tran.highlighted) {
        row.style.backgroundColor = HIGHLIGHT_COLOR
    } else if (tran.categories.includes(28)) {
        row.style.backgroundColor = FEE_COLOR
    }

    col = createEl(
        "td",
        {class: "transaction-cell"},
        // todo: We can only do one or both of this , and descrip flex. We need this to center teh icon,
        // todo and descrip to be horizontal with pending...
        {paddingLeft: "12px", color: "black"}
    ) // Icon

    d = createEl("div", {}, {display: "flex", alignItems: "center"})

    if (EDIT_MODE_TRAN) {
        d.appendChild(createCatEdit(tran))
        col.appendChild(d)

    } else if (tran.id === CAT_QUICKEDIT) {
        d.appendChild(createCatEdit(tran, true, QUICK_CAT_SEARCH)) // Auto-save.

        // h = createEl("h4", {}, {}, "🔎")
        // d.appendChild(h)

        // todo: Put this back.
        // let search = createEl("input", {id: "quick-cat-search"}, {width: "70px"},)
        // search.addEventListener("input", e => {
        //     QUICK_CAT_SEARCH = e.target.value
        //     refreshTransactions()
        // })
        // d.appendChild(search)

        col.appendChild(d)

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

        btn =  createEl("button", {class: "button-small"}, {}, "Cancel")
        btn.addEventListener("click", _ => {
            CAT_QUICKEDIT = null
            CAT_ALWAYS = false
            refreshTransactions()
        })
        d.appendChild(btn)
    } else {
        // Allow clicking to enter quick edit.
        d.style.cursor = "pointer"
        d.addEventListener("click", _ => {
            CAT_QUICKEDIT = tran.id
            refreshTransactions() // Hopefully-safe recursion.
        })

        if (tran.logo_url.length > 0) {
            img = createEl("img", {"src": tran.logo_url, alt: "", width: "20px"})
            d.appendChild(img)
        }

        let s
        if (TRANSACTION_ICONS) {
            s = createEl("span", {}, {}, tran.categories.length ? catIconFromVal(tran.categories[0]) : "")
        } else {
            s = createEl("span", {}, {}, tran.categories.length ? catNameFromVal(tran.categories[0]) : "")
        }

        d.appendChild(s)
        col.appendChild(d)
    }

    row.appendChild(col)

    // Flex for pending indicator.
    col = createEl("td", {class: "transaction-cell"}, {display: "flex"})

    if (EDIT_MODE_TRAN) {
        ip = createEl(
            "input",
            {value: tran.description},
            // {width: "200px"},
        )

        ip.addEventListener("input", e => {
            let updated = {
                ...tran,
                description: e.target.value
            }
            // todo: DRY!
            TRANSACTIONS_UPDATED[String(tran.id)] = updated
        })

        col.appendChild(ip)
    } else {
        h = createEl(
            "h4",
            {class: "tran-heading"},
            {fontWeight: "normal", marginLeft: "0px"},
            tran.description
        )
        col.appendChild(h)

        if (tran.pending) {
            col.appendChild(createEl(
                "h4",
                {class: "tran-heading"},
                {color: "#999999", fontWeight: "normal", marginLeft: "8px"},
                "| Pending")
            )
        }
    }

    row.appendChild(col)

    col = createEl("td", {class: "transaction-cell"}, {})
    if (EDIT_MODE_TRAN) {
        h = createEl("input", {value: tran.notes}, {marginRight: "30px"})

        h.addEventListener("input", e => {
            let updated = {
                ...tran,
                notes: e.target.value
            }
            // todo: DRY!
            TRANSACTIONS_UPDATED[String(tran.id)] = updated
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
                let updated = {
                    ...tran,
                    amount: parseFloat(e.target.value)
                }
                // todo: DRY!
                TRANSACTIONS_UPDATED[String(tran.id)] = updated
            }
        })

    } else {
        h = createEl("h4",
            // {class: "tran-heading " +  tran.amount_class},
            {class: "tran-heading " +  "tran_neutral"},
            {textAlign: "right", marginRight: "40px"}, formatAmount(tran.amount, true)
        )
    }

    col.appendChild(h)
    row.appendChild(col)

    col = createEl("td", {class: "transaction-cell"})
    if (EDIT_MODE_TRAN) {
        d = createEl("div", {}, {display: "flex"})
        h = createEl("input", {type: "date", value: tran.date}, {width: "120px"})

        h.addEventListener("input", e => {
            let updated = {
                ...tran,
                date: e.target.value
            }
            // todo: DRY!
            TRANSACTIONS_UPDATED[String(tran.id)] = updated
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

        d.appendChild(h)
        d.appendChild(delBtn)
        col.appendChild(d)
    } else {
        h = createEl("h4", {class: "tran-heading"}, {}, tran.date_display)

        // Highlighter icon.
        // let s = createEl("span", {}, {marginLeft: "6px", marginRight: 0, backgroundColor: "#fff5e9", cursor: "pointer"}, "🖍️")
        let s = createEl("span", {}, {marginLeft: "6px", marginRight: 0, cursor: "pointer"}, "🖍️")

        s.addEventListener("click", _ => {
            let data = {id: tran.id}
            fetch("/toggle-highlight", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {
                });

            tran.highlighted = !tran.highlighted
            let bgColor = tran.highlighted ? HIGHLIGHT_COLOR : "white"
            getEl("tran-row-" + tran.id.toString()).style.backgroundColor = bgColor
        })

        h.appendChild(s)

        col.appendChild(h)
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

    let col, img, h, opt, sel, d, ip
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
    const data = {
        name: getEl("add-manual-name").value,
        sub_type: parseInt(getEl("add-manual-type").value),
        current: parseInt(getEl("add-manual-current").value),
        iso_currency_code: getEl("add-manual-currency-code").value,
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
            // Save transactions on click

            const data = {
                // Discard keys; we mainly use them for updating internally here.
                transactions: Object.values(TRANSACTIONS_UPDATED)
            }

            // Save transactions to the database.
            fetch("/edit-transactions", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
                .then(result => result.json())
                .then(r => {
                    if (!r.success) {
                        console.error("Transaction save failed")
                    } else {
                        // window.location.reload(); // todo temp until we can update cat in place.
                    }
                });

            refreshTransactions()


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

            TRANSACTIONS_UPDATED = {}

            refreshTransactions()  // Overkill; just to taek out of edit mode. todo: SPlit refreshTransactions.
            EDIT_MODE_TRAN = false
            btn.textContent = "Edit transactions"
        } else {
            // Enable editing on click.
            refreshTransactions()  // Overkill; just to taek out of edit mode. todo: SPlit refreshTransactions.
            EDIT_MODE_TRAN = true
            btn.textContent = "Save transactions"
        }
        refreshTransactions()
    })
}

function setupAccEditForm(id) {
    let acc = ACCOUNTS.filter(a => a.id === id)[0]

    // Setup the form for adding and editing accounts.
    let outerDiv = getEl("account-div")
    outerDiv.style.visibility = "visible"
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


    d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})

    if (acc.manual) {
        h = createEl("h3", {}, {marginTop: 0, marginBottom: "18px"}, "Account name")
        ip = createEl("input", {value: acc.name})
        ip.addEventListener("input", e => {
            let updated = {
                ...acc,
                name: e.target.value
            }
            ACCOUNTS_UPDATED[acc.id] = updated
        })
    } else {
        h = createEl("h3", {}, {marginTop: 0, marginBottom: "18px"}, "Nickname")
        ip = createEl("input", {value: acc.nickname})
        ip.addEventListener("input", e => {
            let updated = {
                ...acc,
                nickname: e.target.value
            }
            ACCOUNTS_UPDATED[acc.id] = updated
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
        h = createEl("h3", {}, {marginTop: 0, marginBottom: "18px"}, "Currency code")
        ip = createEl("input", {value: acc.iso_currency_code, maxLength: "3"})

        ip.addEventListener("input", e => {
            let updated = {
                ...acc,
                iso_currency_code: e.target.value
            }
            ACCOUNTS_UPDATED[acc.id] = updated
            refreshAccounts()
        })

        d.appendChild(h)
        d.appendChild(ip)
        form.appendChild(d)
    }

    if (acc.manual) {
        d = createEl("div", {}, {alignItems: "center", justifyContent: "space-between"})
        h = createEl("h3", {}, {}, "Value")
        ip = createEl("input", {type: "number", value: acc.current})

        ip.addEventListener("input", e => {
            let updated = {
                ...acc,
                current: parseFloat(e.target.value)
            }
            ACCOUNTS_UPDATED[acc.id] = updated
            refreshAccounts()
        })

        d.appendChild(h)
        d.appendChild(ip)
        form.appendChild(d)
    }

    d = createEl("div", {}, {display: "flex", justifyContent: "center", marginTop: "18px"})
    let btnSave = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "💾Save")
    let btnCancel = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "Cancel")

    let btnDelete = createEl("button", {type: "button", class: "button-general"}, {width: "140px"}, "❌Delete")
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


        outerDiv.style.visibility = "collapse"
    })

    btnCancel.addEventListener("click", _ => {
        ACCOUNTS_UPDATED = {}
        outerDiv.style.visibility = "collapse"
    })

    // todo: Confirmation.
    btnDelete.addEventListener("click", _ => {
        let data = {ids: [acc.id]}
        fetch("/delete-accounts", { body: JSON.stringify(data), ...FETCH_HEADERS_POST })
            .then(result => result.json())
            .then(r => {
                if (!r.success) {
                    console.error("Account edits save failed")
                }
            });
        ACCOUNTS = ACCOUNTS.filter(a => a.id !== acc.id)
        refreshAccounts()
        outerDiv.style.visibility = "collapse"
    })

    d.appendChild(btnSave)
    d.appendChild(btnCancel)
    d.appendChild(btnDelete)
    form.appendChild(d)
}

function setupSpendingHighlights() {
    // Consider a template for this instead; it should be faster.
    let biggestCats  = getEl("biggest-cats")

    let h, text

    h = createEl(
        "h3",
        {},
        {marginRight: "40px"},
        "Total: "
    )

    let s = createEl("span", {class: "tran_neutral"}, {}, formatAmount(SPENDING_HIGHLIGHTS.total, 0))
    h.appendChild(s)
    biggestCats.appendChild(h)

    for (let highlight of SPENDING_HIGHLIGHTS.by_cat.slice(0, 3)) {
        text = catIconFromVal(highlight[0]) + catNameFromVal(highlight[0]) + ": "
        h = createEl(
            "h4",
            {},
            {marginRight: "40px", cursor: "pointer", fontWeight: "normal"},
            text
        )
        let s = createEl("span", {class: "tran_neutral"}, {fontWeight: "bold"}, formatAmount(highlight[1][1], 0))

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

    h = createEl("h4", {}, {}, "Spending: ")
    let s2 = createEl(
        "span",
        // {class: SPENDING_HIGHLIGHTS.total_change >= 0. ? "tran_pos" : "tran_neg"},
        {class: "tran_neutral"},
        {fontWeight: "bold"},
        formatAmount(SPENDING_HIGHLIGHTS.total_change, 0)
    )

    h.appendChild(s2)
    changes.appendChild(h)

    for (let catChange of SPENDING_HIGHLIGHTS.cat_changes.slice(0, 3)) {

        // todo: + sign explicitly if spending went up.
        h = createEl(
            "h4",
            {},
            {fontWeight: "normal", cursor: "pointer"},
            catIconFromVal(catChange[0]) + catNameFromVal(catChange[0]) + ": "
        )
        let s = createEl("span", {class: "tran_neutral"}, {fontWeight: "bold"}, formatAmount(catChange[1], 0))
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

    if (SPENDING_HIGHLIGHTS.large_purchases.length === 0) {
        h = createEl(
            "h4",
            {},
            // {marginRight: "40px", cursor: "pointer"},
            {marginRight: "40px", fontWeight: "normal"},
            "(None)"
        )
        largePurchases.appendChild(h)
    }

    for (let purchase of SPENDING_HIGHLIGHTS.large_purchases.slice(0, 3)) {
        text = purchase.description + ": "
        h = createEl(
            "h4",
            {},
            // {marginRight: "40px", cursor: "pointer"},
            {marginRight: "40px", fontWeight: "normal"},
            text
        )
        let s = createEl("span", {class: "tran_neutral"}, {fontWeight: "bold"}, formatAmount(purchase.amount, 0))
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

    let sel = createEl("select", {id: "tran-filter-sel"}, {height: "40px"})

    let opt = createEl("option", {value: -2}, {}, "All categories")
    sel.appendChild(opt)

    for (let cat of catNames) {
        opt = createEl("option", {value: cat[0]}, {}, cat[1])
        sel.appendChild(opt)
    }

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
                console.log("Link token set: ", LINK_TOKEN)
                getPublicToken()
            });
    });

    refreshAccounts()
    refreshTransactions()

    let check = getEl("icon-checkbox")
    check.addEventListener("click", _ => {
        TRANSACTION_ICONS = !TRANSACTION_ICONS
        refreshTransactions() // todo: Dangerous potentially re infinite recursions, but seems to be OK.
    })

    setupEditTranButton()

    // Tell the backend to start updating account data values etc, and receive updates based on that here.
    fetch("/post-dash-load", FETCH_HEADERS_GET)
        // Parse JSON if able.
        .then(result => result.json())
        .then(r => {
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
        });

    setupSpendingHighlights()
    setupCatFilter()

    if (onMobile()) {
        getEl("biggest-change-h").textContent = "Changes:"
        getEl("large-purchases-h").textContent = "Large:"
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
        // id: tempId,
        amount: 0.,
        // amount_class: "tran_pos",
        amount_class: "tran_neutral",
        categories: [-1],
        // categories_icon: [],
        // categories_text: [],
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
    // TRANSACTIONS.push(newTran)

    const payload = {transactions: [newTran]}

    fetch("/add-transactions", { body: JSON.stringify(payload), ...FETCH_HEADERS_POST })
        .then(result => result.json())
        .then(r => {
            // // We could just hold off on adding the transaction to the UI, but I think this approach
            // // will feel more responsive due to showing the tran immediately.
            // TRANSACTIONS = TRANSACTIONS.filter(t => t.id !== tempId0)

            if (r.success) {
                console.log("Add resp: ", r)
                TRANSACTIONS.push({
                    ...newTran,
                    id: r.ids[0],
                })

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

    if (form.style.visibility === "visible") {
        form.style.visibility = "collapse"
        // btnToggle.textContent = "➕ Manual account"
        btnToggle.style.visibility = "visible"
    } else {
        form.style.visibility = "visible"
        btnToggle.style.visibility = "hidden"
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

document.addEventListener("keydown",function(e){
    if(e.key === "Escape") {
        CAT_QUICKEDIT = null
        CAT_ALWAYS = false
        refreshTransactions() // todo: Don't refresh all. just the text edit in question.
    }
});