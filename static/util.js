function isValidNumber(str) {
    // First, try parsing the string
    const num = parseFloat(str);

    // Check if the parsed number is NaN. If so, it's not a valid number.
    if (isNaN(num)) {
        return false;
    }

    // Then check if the string representation of the parsed number matches the input.
    // This ensures that inputs like "123abc" or "123.45.67" are rejected.
    // Trim the input to ignore leading/trailing whitespace.
    const trimmedInput = str.trim();

    // Create a regular expression to match the possible string representations of the parsed number.
    // This accounts for both integer and floating-point numbers, including those in exponential notation.
    const regexPattern = new RegExp("^" + num + "$|^" + num + "e[+-]?\\d+$", "i");

    // Test the trimmed input against the regular expression.
    return regexPattern.test(trimmedInput);
}

function createEl(tag, attributes, style, text) {
    // Create and return an element with given attributes and style.
    let el = document.createElement(tag)

    if (attributes) {
        for (const [attr, val] of Object.entries(attributes)) {
            el.setAttribute(attr, val)
        }
    }

    if (style) {
        for (const [attr, val] of Object.entries(style)) {
            el.style[attr] = val
        }
    }

    if (text) {
        el.textContent = text
    }

    return el
}

function accTypeFromNum(val) {
    // See models.py
    if (val === 0) {
        return "Checking"
    }
    if (val === 1) {
        return "Savings"
    }
    if (val === 2) {
        return "Debit"
    }
    if (val === 3) {
        return "Credit"
    }
    if (val === 4) {
        return "401K"
    }
    if (val === 5) {
        return "Student"
    }
    if (val === 6) {
        return "Mortgage"
    }
    if (val === 7) {
        return "Cd"
    }
    if (val === 8) {
        return "Money market"
    }
    if (val === 9) {
        return "IRA"
    }
    if (val === 10) {
        return "Mutual fund"
    }
    if (val === 11) {
        return "Crypto"
    }

    if (val === 12) {
        return "Asset"
    }

    if (val === 13) {
        return "Brokerage"
    }

    if (val === 14) {
        return "Roth"
    }
}

function catNameFromVal(val){
    // See transaction_cats.py

    if (val === -1) {
        return "Uncategorized"
    }
    if (val === 0) {
        return "Food and drink"
    }
    if (val === 1) {
        return "Restaurants"
    }
    // if (val === 2) {
    //     return "a"
    // }
    if (val === 3) {
        return "Travel"
    }
    if (val === 4) {
        return "Airlines"
    }
    if (val === 5) {
        return "Recreation"
    }
    if (val === 6) {
        return "Gyms"
    }
    if (val === 7) {
        return "Transfer"
    }

    if (val === 8) {
        return "Desposit"
    }
    if (val === 9) {
        return "Payroll"
    }
    if (val === 10) {
        return "Credit card"
    }
    if (val === 11) {
        return "Fast food"
    }
    if (val === 12) {
        return "Debit card"
    }
    if (val === 13) {
        return "Shops"
    }
    if (val === 14) {
        return "Payment"
    }
    if (val === 15) {
        return "Coffee shop"
    }

    // todo: Finish
    if (val === 16) {
        return "Taxi"
    }
    if (val === 17) {
        return "Sporting goods"
    }
    if (val === 18) {
        return "Electronics"
    }
    if (val === 19) {
        return "Pets"
    }
    if (val === 20) {
        return "Children"
    }
    if (val === 21) {
        return "Mortgage and rent"
    }
    if (val === 22) {
        return "Car"
    }
    if (val === 23) {
        return "Home and garden"
    }
    if (val === 24) {
        return "Medical"
    }
    if (val === 25) {
        return "Entertainment"
    }
    if (val === 26) {
        return "Bills and utilities"
    }
    if (val === 27) {
        return "Investments"
    }
    if (val === 28) {
        return "Fees"
    }
    if (val === 29) {
        return "Taxes"
    }
    if (val === 30) {
        return "Business  services"
    }
    if (val === 31) {
        return "Cash and checks"
    }
    if (val === 32) {
        return "Gifts"
    }
    if (val === 33) {
        return "Education"
    }

    console.error("Fallthrough on cat name")
    return "Uncategorized"
}