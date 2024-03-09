const FETCH_HEADERS_GET = {
    method: "GET",
    mode: "cors",
    credentials: "same-origin",
    headers: {
        "X-CSRFToken": getCrsfToken(),
        Accept: "application/json",
    },
}
const FETCH_HEADERS_POST = {
    method: "POST",
    mode: "cors",
    credentials: "same-origin",
    headers: {
        "X-CSRFToken": getCrsfToken(),
        Accept: "application/json",
    },
}

// Global mutal variables
let LINK_TOKEN = ""
let SEARCH_TEXT = ""
let FILTER_START = "1999-09-09"  // todo!
let FILTER_END = "2040-09-09"  // todo!
let VALUE_THRESH = 0
let CURRENT_PAGE = 0

// Whenever we change page, or filter terms, we may need to load transactions. This tracks
// if we've already done so, for a given config
let TRANSACTIONS_LOADED = true

const PAGE_SIZE = 40


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

    let transactions
    // todo: Use TRANSACTIONS_DISPLAYED?
    // Note: This truthy statement catches both an empty string, and an undefined we get on init.
    if (!searchText) {
        transactions = TRANSACTIONS
    } else {
        transactions = TRANSACTIONS.filter(t => {
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

    transactions.sort((b, a) => new Date(a.date) - new Date(b.date))

    const startI = CURRENT_PAGE * PAGE_SIZE
    const endI = CURRENT_PAGE * PAGE_SIZE + PAGE_SIZE

    transactions = transactions.slice(startI, endI)

    console.log(startI, endI, transactions, transactions.length, "Start, end, tran")

    if (!TRANSACTIONS_LOADED) {  // A check against doing this multiple times (or finititely) in a row.
        console.log("Trans not loaded")
        TRANSACTIONS_LOADED = true

        // If, after filtering, we don't have a full page of information, request more from the backend.
        if (transactions.length < PAGE_SIZE) {
            console.log("Requesting more transactions...")
            const data = {start_i: startI, end_i: endI, search: SEARCH_TEXT, start: FILTER_START, end: FILTER_END} // todo: Doesn't have to be page size.

            fetch("/load-transactions", {body: JSON.stringify(data), ...FETCH_HEADERS_POST})
                .then(result => result.json())
                .then(r => {
                    console.log("Load result: ", r)

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

function formatNumber(number, decimals) {
    // Format a currency value with commas, and either 2, or 0 decimals.
    let options = decimals ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } :
        { minimumFractionDigits: 0, maximumFractionDigits: 0 }
    return new Intl.NumberFormat('en-US', options).format(number);
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
    const valueFormatted = formatNumber(val, false)
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

    let section = document.getElementById("accounts")
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
            totalFormatted = formatNumber(total, false)
            h2 = createEl("h2", {class: class_}, {marginTop: 0, marginBottom: 0, textAlign: "center"}, totalFormatted) // total todo

            div.appendChild(h1)
            div.appendChild(h2)
        }

        for (let acc of accs[0]) {
            div.appendChild(createAccRow(acc, accs[1]))
        }

        if (accs[0].length > 0) {
            section.appendChild(div)
        }
    }
}

function refreshTransactions() {
    //[Re]populate the transactions table based on state.
    console.log("Refreshing transactions...")

    let transactions = filterTransactions()

    let tbody = document.getElementById("transaction-tbody")
    tbody.replaceChildren();

    let col, img
    for (let tran of transactions) {
        const row = document.createElement("tr")

        col = document.createElement("td") // Icon

        if (tran.logo_url.length > 0) {
            img = createEl("img", {"src": tran.logo_url, alt: "", width: "20px"})
            col.appendChild(img)
        }

        // todo: Put back once the icon is sorted.
        let s
        if (TRANSACTION_ICONS) {
            s = createEl("span", {}, {}, tran.categories_icon)
            // col.textContent = tran.categories_icon
        } else {
            // col.textContent = tran.categories_text
            s = createEl("span", {}, {}, tran.categories_text)
        }
        col.appendChild(s)
        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        let h = createEl(
            "h4",
            {class: "tran-heading"},
            {fontWeight: "normal", marginLeft: "40px"},
            tran.description
        )
        col.appendChild(h)

        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
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
                {class: "tran-heading " +  tran.amount_class},
                {textAlign: "right", marginRight: "40px"}, formatNumber(tran.amount, true)
            )
        }

        col.appendChild(h)

        row.appendChild(col)

        col = createEl("td", {class: "transaction-cell"})
        if (EDIT_MODE_TRAN) {
            h = createEl("input", {type: "date", value: tran.date}, {width: "120px"})

            h.addEventListener("input", e => {
                let updated = {
                    ...tran,
                    date: e.target.value
                }
                // todo: DRY!
                TRANSACTIONS_UPDATED[String(tran.id)] = updated
            })
        } else {
            h = createEl("h4", {class: "tran-heading"}, {}, tran.date_display)
        }
        col.appendChild(h)

        row.appendChild(col)

        tbody.appendChild(row)
    }
}

function updateTranFilter() {
    TRANSACTIONS_LOADED = false // Allows more transactions to be loaded from the server.

    SEARCH_TEXT = document.getElementById("search").value.toLowerCase()

    // todo: Enforce integer value.
    let valueThresh = document.getElementById("transaction-value-filter").value
    // Remove non-integer values

    // todo: number field here is actually interfering, returning an empty string if invalid;
    // so, we can't just ignore chars.

    VALUE_THRESH = parseInt(valueThresh.replace(/\D+/g, ''))

    FILTER_START = document.getElementById("tran-filter-start").value
    FILTER_END = document.getElementById("tran-filter-end").value
    refreshTransactions()
}


function getCrsfToken() {
    // For CRSF compatibility
    let name_ = "csrftoken"
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name_.length + 1) === (name_ + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name_.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function addAccountManual() {
    // We use this when submitting a new manual account
    // document.getElementById("add-account-manaul").addEventListener("click", _ => {
    //                 <input id="add-manual-name" />
    //
    //                 <select id="add-manual-type" style="border: 1px solid black; height: 32px; width: 156px;">
    //
    //                 <input id="add-manual-current" type="number" value="0" />

    // todo: Validate no blank account name
    const data = {
        name: document.getElementById("add-manual-name").value,
        sub_type: parseInt(document.getElementById("add-manual-type").value),
        current: parseInt(document.getElementById("add-manual-current").value),
        iso_currency_code: document.getElementById("add-manual-currency-code").value,
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
    let btn = document.getElementById("edit-transactions");

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
                    }
                });

            // Update transactions in place, so a refresh isn't required.
            for (let tran of Object.values(TRANSACTIONS_UPDATED)) {
                let date = new Date(tran.date)
                tran.date_display = (date.getUTCMonth() + 1) % 12 + "/" + date.getUTCDate()
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
    let outerDiv = document.getElementById("account-div")
    outerDiv.style.visibility = "visible"
    let form = document.getElementById("account-form")
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

    let acc_input_name = ""

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

function init() {
    // We run this on page load
    document.getElementById("link-button").addEventListener("click", _ => {
        fetch("/create-link-token", FETCH_HEADERS_GET)
            // Parse JSON if able.
            .then(result => result.json())
            .then(r => {
                LINK_TOKEN = r.link_token
                console.log("Link token set: ", LINK_TOKEN)
                getPublicToken()
            });
    });

    document.getElementById('export').addEventListener('click', function() {
        window.location.href = '/export'
    })

    document.getElementById('export').addEventListener('click', function() {
        window.location.href = '/export'
    })

    // Set up the import start
    const importStart = document.getElementById('import-start')
    importStart.addEventListener('click', function() {
        // importStart.
        const importForm = document.getElementById("import-form")
        if (importForm.style.visibility === "collapse") {
            importForm.style.visibility = "visible"
            // importStart.style.visibility = "collapse"
        } else {
            importForm.style.visibility = "collapse"
        }

    })

    refreshAccounts()
    refreshTransactions()

    let check = document.getElementById("icon-checkbox")
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
            console.log("Post dash load data: ", r)
        });
}

init()

function toggleAddManual() {
    let form = document.getElementById("add-manual-form")
    let btnToggle = document.getElementById("add-manual-button")

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
    console.log("Page: ", CURRENT_PAGE)

    TRANSACTIONS_LOADED = false // Allows more transactions to be loaded from the server.
    refreshTransactions()
}