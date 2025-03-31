class CreditCardGenerator {
    constructor() {
        this.bins = {
            'Visa': ['4'],
            'Mastercard': ['51', '52', '53', '54', '55'],
            'American Express': ['34', '37'],
            'Discover': ['6011', '644', '645', '646', '647', '648', '649', '65'],
            'JCB': ['35']
        };
    }

    // Luhn algorithm for card number validation
    luhnCheck(num) {
        let arr = (num + '').split('').reverse().map(x => parseInt(x));
        let sum = arr.reduce((acc, val, i) => {
            if (i % 2 !== 0) {
                val = val * 2;
                if (val > 9) val = val - 9;
            }
            return acc + val;
        }, 0);
        return sum % 10 === 0;
    }

    // Generate check digit using Luhn algorithm
    generateCheckDigit(partial) {
        for(let i = 0; i <= 9; i++) {
            if(this.luhnCheck(partial + i)) {
                return i;
            }
        }
        return 0;
    }

    // Generate random numbers of specified length
    generateRandomNumbers(length) {
        let result = '';
        for(let i = 0; i < length; i++) {
            result += Math.floor(Math.random() * 10);
        }
        return result;
    }

    // Generate expiry date
    generateExpiryDate() {
        const currentYear = new Date().getFullYear();
        const month = Math.floor(Math.random() * 12) + 1;
        const year = currentYear + Math.floor(Math.random() * 5) + 1;
        return {
            month: month.toString().padStart(2, '0'),
            year: year.toString().slice(-2)
        };
    }

    // Generate CVV
    generateCVV(cardType) {
        const length = cardType === 'American Express' ? 4 : 3;
        return this.generateRandomNumbers(length);
    }

    // Generate card number with custom BIN
    generateCardNumber(cardType, customBin = '') {
        let length = cardType === 'American Express' ? 15 : 16;
        let number;

        if (customBin) {
            // Use custom BIN
            const remainingLength = length - (customBin.length + 1);
            const partial = customBin + this.generateRandomNumbers(remainingLength);
            const checkDigit = this.generateCheckDigit(partial);
            number = partial + checkDigit;
        } else {
            // Use default BIN
            const bins = this.bins[cardType];
            const bin = bins[Math.floor(Math.random() * bins.length)];
            const remainingLength = length - (bin.length + 1);
            const partial = bin + this.generateRandomNumbers(remainingLength);
            const checkDigit = this.generateCheckDigit(partial);
            number = partial + checkDigit;
        }

        return number;
    }

    // Format card number for display
    formatCardNumber(number, cardType) {
        if (cardType === 'American Express') {
            return number.replace(/(\d{4})(\d{6})(\d{5})/, '$1 $2 $3');
        }
        return number.replace(/(\d{4})(?=\d)/g, '$1 ');
    }

    // Generate complete card details with optional custom values
    generateCard(cardType, options = {}) {
        const number = this.generateCardNumber(cardType, options.bin || '');
        const expiry = options.expiry || this.generateExpiryDate();
        const cvv = options.cvv || this.generateCVV(cardType);
        
        return {
            type: cardType,
            number: number,
            formattedNumber: this.formatCardNumber(number, cardType),
            expiry: expiry,
            cvv: cvv,
            bin: number.slice(0, 6)
        };
    }

    // Get available card types
    getCardTypes() {
        return Object.keys(this.bins);
    }

    // Validate a card number
    validateCard(number) {
        return this.luhnCheck(number.replace(/\s/g, ''));
    }

    // Get card type from number
    getCardTypeFromNumber(number) {
        number = number.replace(/\s/g, '');
        for (let [type, prefixes] of Object.entries(this.bins)) {
            if (prefixes.some(prefix => number.startsWith(prefix))) {
                return type;
            }
        }
        return 'Unknown';
    }

    // Validate BIN
    validateBIN(bin) {
        return /^\d{6}$/.test(bin);
    }

    // Validate expiry date
    validateExpiry(month, year) {
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;
        
        const expYear = 2000 + parseInt(year);
        const expMonth = parseInt(month);

        if (expMonth < 1 || expMonth > 12) return false;
        if (expYear < currentYear) return false;
        if (expYear === currentYear && expMonth < currentMonth) return false;

        return true;
    }

    // Validate CVV
    validateCVV(cvv, cardType) {
        const length = cardType === 'American Express' ? 4 : 3;
        return new RegExp(`^\\d{${length}}$`).test(cvv);
    }

    // Get BIN information
    async getBINInfo(bin) {
        try {
            const response = await fetch(`https://lookup.binlist.net/${bin}`);
            if (!response.ok) throw new Error('BIN lookup failed');
            return await response.json();
        } catch (error) {
            console.error('BIN lookup error:', error);
            return null;
        }
    }
}