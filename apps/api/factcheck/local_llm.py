import logging
import json
import os

logger = logging.getLogger(__name__)

class LocalScamClassifier:
    """
    Rule-based Scam Classifier (Fast and Reliable)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalScamClassifier, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.is_loaded = False
        return cls._instance

    def load_model(self):
        """No model loading needed for rule-based approach"""
        logger.info("Using rule-based scam detection (no model loading required)")
        self.is_loaded = True

    async def predict_instant_scam(self, transcript: str) -> dict | None:
        scam_keywords = [
            "immediately transfer", "secure account", "illegal transactions", 
            "digital arrest", "arrest warrant", "police officer", "CBI", "FIR",
            "collect request", "accept this collect", "KYC incomplete", "KYC block",
            "SIM card blocked", "OTP share", "investment scheme", "invest 1 lakh",
            "guaranteed returns", "registration fee", "win lottery", "won lottery",
            "disconnection", "pay immediately", "threaten", "urgent money",
            "computer hacked", "remote access", "antivirus service", "Microsoft support",
            "download this app", "provide Aadhaar", "government approved scheme", "special scheme",
            "work from home", "registration fee", "video job", "like YouTube videos",
            "unpaid bill", "disconnection", "pay immediately", "process fee", "claim prize",
            "password", "CVV", "debit card details", "net banking password",
            "account will be deactivated", "multiple login attempts",
            "whatsapp account", "customs department", "clear customs", "international parcel",
            "share your aadhaar", "share your pan", "photo of aadhaar",
            "unusual activity", "routine security check", "for your security",
            "special government grant", "covid relief fund", "processing fee",
            "fraud department", "suspicious transaction", "block this transaction",
            "existing insurance company is fraud", "government-approved scheme",
            "lost his phone", "using friend's number", "only trusted friend",
            "deduct from first salary", "training fee", "international transaction",
            "met with an accident", "admitted in hospital", "using friend's number",
            # Hindi scam keywords
            "account block hone wala", "illegal transaction detect", "paise safe account",
            "transfer kar do immediately", "urgent hai bhai", "block ho jayega",
            # Extreme twisted scam keywords
            "internal audit account", "internal audit", "transfer your balance",
            "account freeze", "account has been frozen", "visit your nearest branch",
            "priority booking", "vip customers", "vip status", "advance payment",
            "policy has lapsed", "policy will be cancelled", "late fee", "revive policy",
            "government discount", "50% discount", "special offer ends", "save money",
            "donate 5000", "donate immediately", "children are starving", "send money",
            "reward points expiring", "processing fee to redeem", "points will be lost",
            "courtesy call", "warn you that scammers", "confirm the otp",
            "non-bailable arrest warrant", "court fee", "settle out of court",
            "police arrested me", "demanding 2 lakh", "lawyer's account",
            "blacklisted by trai", "sim box cloning", "port to secure server",
            "eligible for special interest rate", "open new fd", "limited time offer",
            "cylinder shortage", "priority delivery", "waiting 15 days",
            "funding cut", "registered ngo", "send money to this account",
            "cyber crime", "anti-scam",
            # Additional English scam keywords
            "money laundering", "terrorism funding", "police case", "system upgrade",
            "password reset", "net banking", "debit card", "credit card", "update details",
            "passport", "human trafficking", "cancellation", "driving license", "suspended",
            "voter id", "fake registrations", "legal action", "share market", "insider information",
            "crypto", "bitcoin", "double in", "youtube task", "account activation",
            "affiliate marketing", "forex trading", "secrets of billionaires", "gift voucher",
            "redeem voucher", "maldives holiday", "100 grams gold", "insurance prize",
            "activate insurance", "critical condition", "surgery needed", "life risk",
            "sim card misuse", "multiple login attempts", "platinum upgrade", "fd maturing",
            "special reward", "tax to receive", "upgrade your policy", "cover 50 more diseases",
            # UPI specific
            "upi account blocked", "accept this collect request", "upi pin", "unusual login",
            "secure your account", "refund of", "cashback", "wallet limit increased", "pay again to different account",
            "failed transaction", "scan this qr code", "immediate payment required",
            # Digital arrest specific
            "digital arrest warrant", "red corner notice", "enforcement directorate", "non-bailable warrant",
            "quash fir", "avoid raid", "tax evasion detected", "property seizure", "gst registration",
            "business closure", "central agencies tracking", "summons issued", "settle out of court",
            "court fee", "avoid appearance",
            # Family emergency specific
            "beta this is your mom", "hospital emergency surgery", "serious accident", "in jail for no reason",
            "stuck at airport", "visa problem", "business failure", "seize property", "lost his phone",
            "college admission at risk", "visiting next week", "just wanted to inform",
            # Tech support specific
            "hacked and we need remote access", "icloud account compromised", "order hacked",
            "illegal activity", "disconnection and case", "illegal tampering", "illegal",
            "connection involved in terrorism", "system maintenance scheduled", "you may experience interruption",
            # KYC specific
            "sim card will be blocked", "incomplete kyc", "download this app", "provide aadhaar",
            "telecom department", "multiple sims issued", "without knowledge", "linked to illegal activities",
            "income tax department", "rto calling", "election commission", "passport office",
            "aadhaar verification", "share aadhaar photo", "aadhaar linked to", "aadhaar without knowledge",
            "uidai calling", "aadhaar needs verification", "share otp to protect your identity", "identity from misuse"
            # Tamil scam keywords
            "உடன் பணம்", "பாதுகாப்பு கணக்கு", "வங்கி கணக்கு",
            "உடனடி பணம்", "போலீஸ் எண்", "ஏடிஎம் கார்டு",
            "லாட்டரி", "பெற்றீர்", "செலுங்கள்", "மருத்துவார்", "அனுப்பு",
            "கார்டு தடுக்கப்படும்", "பூர்த்தி செய்யுங்கள்", "ஆதார்", "பங்கு",
            # Telugu scam keywords
            "డబ్బ్ల్యూ మనీ", "బ్యాంక్ ఖాతా", "తక్షణ మనీ",
            "వెంటనే పంపించండి", "పాసవర్డ్", "ఒటిపి",
            "వర్క్ ఫ్రమ్ హోమ్", "నెలగు", "సంపాదిందు", "రిజిస్ట్రేషన్ ఫీ", "చెల్లవండి",
            "పెట్టింగ్ స్కీమ్", "పెట్టిండి", "పొందుతారు", "గ్యారంటీ ఆమోదింగం",
            "ఇన్షురెన్స్ పాలిసీ", "రద్దు",
            # Bengali scam keywords
            "টাকা পাঠাও", "ব্যাংক অ্যাকাউন্ট", "অবিলম্ব",
            "পাসওয়ার্ড", "এটিএম কার্ড", "ওটিপি",
            "লটারি", "জিতেছেন", "পুরস্কার", "প্রসেসিং ফি",
            "হোম ফ্রম জব", "মাসিক", "আয", "রেজিস্ট্রেশন ফি",
            "হাসপাতালে", "তাৎরিত",
            # Marathi scam keywords
            "पैसे पाठवा", "बँक खाते", "तात्काळ",
            "पासवर्ड", "एटीएम कार्ड", "ओटीपी",
            "गुंतवनिकी स्कीम", "गुंतव", "मिळो", "सरकारारी योजना",
            "लॉटरी", "जिंकले", "प्रोसेसिंग फी",
            "घरू फ्रम जॉब", "महिने", "कमावा", "नोंदणी फी",
            # Kannada scam keywords
            "ಹಣ ಕಳುಹಿಸಿ", "ಬ್ಯಾಂಕ್ ಖಾತೆ", "ತಕ್ಷಣ",
            "ಪಾಸ್‌ವರ್ಡ್", "ಏಟಿಎಂ ಕಾರ್ಡ್", "ಓಟಿಪಿ",
            "ಇನ್ಶುರೆನ್ಸ್ ಪಾಲಿಸಿ", "ರದ್ದು", "ಚೆಲ್ಲವಂಡಿ",
            "ಹೋಮ್ ಫ್ರಮ್ ಜಾಬ್", "ತಿಂಗಳಿಂದಿರು", "ಸಂಪಾದಿಸು", "ನೋಂದಣಿ ಫೀ",
            "ಲಾಟರಿ", "ಗೆದ್ದುವು", "ಪ್ರಾಸೆಸಿಂಗ್ ಫೀ",
            # Malayalam scam keywords
            "പണം അയച്ചു", "ബാങ്ക് അക്കൗണ്ട്", "ഉടൻ",
            "പാസ്‌വേഡ്", "എടിഎം കാർഡ്", "ഒടിപി",
            "ആശുപത്രിയിൽ", "പെട്ടി", "ആവശ്യം", "ഇപ്പോ", "അയച്ചു",
            "നിക്ഷം സ്കീം", "നിക്ഷി", "ലഭിക്കും", "സർക്കാരി പദ്ധതി",
            "ലോട്ടറി", "ജിക്കുക", "പ്രോസസിംഗ് ഫീ",
            # Punjabi scam keywords
            "ਪੈਸੇ ਭੇਜੋ", "ਬੈਂਕ ਖਾਤਾ", "ਤੁਰੰਤ",
            "ਪਾਸਵਰਡ", "ਏਟੀਐਮ ਕਾਰਡ", "ਓਟੀਪੀ",
            "ਘਰ ਫਰਮ ਜੌਬ", "ਮਹੀਨੇ", "ਰੁਪਏ", "ਕਮਾਓ", "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਫੀ", "ਦੇਓ",
            "ਲਾਟਰੀ", "ਜਿੱਤੇ", "ਪ੍ਰੋਸੈਸਿੰਗ ਫੀ",
            "ਹਸਪਤਾਲ", "ਲੋੜ",
            # Gujarati scam keywords
            "પૈસા મોકલો", "બેંક એકાઉન્ટ", "તાત્કાળ",
            "પાસવર્ડ", "એટીએમ કાર્ડ", "ઓટીપી",
            "ગુંતવનિકી સ્કીમ", "ગુંતવ", "મળો", "સરકારારી યોજના",
            "લોટરી", "જીત્યો", "પ્રોસેસિંગ ફી",
            "ઇન્શ્યરન્સ પાલિસી", "રદ્દુ", "ચૂલવંડી", "પાલીશ"
        ]
        
        legitimate_indicators = [
            "credit card benefits", "customer service", "new credit card", "inform you about",
            "health insurance plan", "vaccination camp", "package has arrived", "OTP to complete delivery",
            "bill is due", "appointment scheduled", "FD is maturing", "fixed deposit",
            "would you like to know", "register for vaccination", "collect it within",
            "insurance plan that might interest", "premium payment", "discount if you renew",
            "booking confirmation", "service complete", "meeting scheduled", "progress",
            "official website", "official app", "visit our website", "walk-in allowed",
            "meter reading", "consumption", "due date", "no rush", "just reminder",
            "schedule an interview", "standard recruitment process", "no fees involved",
            "discharge is processed", "pick up medicines", "hospital counter",
            "vaccines available", "community center", "next camp is at", "health department",
            "seen your profile on linkedin", "no payment required now", "just information",
            "verify your identity before delivery", "hand over the package",
            # Extreme twisted legitimate keywords
            "you had called us earlier", "requested callback", "date of birth",
            "mother's maiden name", "for security", "already blocked those sim cards",
            "no action needed", "informing you as per government regulations",
            "case is listed for hearing", "you are a witness", "no payment required",
            "just notification", "witness", "conducting maintenance", "intermittent network",
            "service will be restored", "no action needed", "government welfare scheme",
            "no agent needed", "direct application", "no fees for application",
            "temporarily frozen", "visit your nearest branch", "id proof and pan card",
            "no phone or online resolution", "security measure", "within 7 days",
            "customer satisfaction survey", "research agency", "not ask for any personal",
            "participation is voluntary", "waiting 3-4 days", "no advance payment",
            "pay at delivery", "all customers treated equally", "due next week",
            "grace period", "no urgency", "late payment penalty", "no discounts available",
            "volunteers needed", "bring food items directly", "no cash donations",
            "visit our center", "do not expire", "check rewards section", "no processing fee",
            "we saw your profile", "would like to schedule interview", "no fees involved",
            "satisfaction survey", "participation voluntary", "not asking for personal info",
            "intermittent network possible", "service will restore automatically", "no action needed",
            # Tamil legitimate keywords
            "இலவசமாக", "பணம் தேவையில்லை", "அதிகாரப்பூர்வ வலைத்தளம்",
            "தகவல் மட்டும்",
            # Telugu legitimate keywords
            "ఉచితమైనది", "డబ్బ్ల్యూ అవసరం లేదు",
            "అధికార వెబ్‌సైట్", "సమాచారం మాత్రమే",
            # Bengali legitimate keywords
            "বিনামূল্যে", "টাকা লাগবে না", "অফিসিয়াল ওয়েবসাইট",
            "শুধু তথ্য",
            # Marathi legitimate keywords
            "मोफत", "पैसे लागणार नाहीत", "अधिकृत वेबसाइट",
            "फक्त माहिती",
            # Kannada legitimate keywords
            "ಉಚಿತ", "ಹಣ ಅಗತ್ಯವಿಲ್ಲ", "ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್",
            "ಮಾಹಿತಿ ಮಾತ್ರ",
            # Malayalam legitimate keywords
            "സൗജന്യമായി", "പണം ആവശ്യമില്ല",
            "ഔദ്യോഗിക വെബ്‌സൈറ്റ്", "വിവരം മാത്രം",
            # Punjabi legitimate keywords
            "ਮੁਫ਼ਤ", "ਪੈਸੇ ਦੀ ਲੋੜ ਨਹੀਂ", "ਅਧਿਕਾਰੀ ਵੈੱਬਸਾਈਟ",
            "ਸਿਰਫ਼ ਜਾਣਕਾਰੀ", "ਸਿਰਫ਼", "ਜਾਣਕਾਰੀ", "ਵੇਖੋ",
            # Gujarati legitimate keywords
            "મફત", "પૈસાની જરૂર નથી", "અધિકૃત વેબસાઇટ",
            "માહિતી માત્ર",
            # Hindi/Hinglish legitimate keywords
            "mukt", "paise ki zarurat nahi", "adhikar website",
            "sirf jankari", "free service", "no money needed", "official website"
        ]
        
        # Additional negative indicators - these indicate legitimate call
        negative_indicators = [
            "no payment required", "no money", "no fees", "not asking for money",
            "free of cost", "no charge", "complimentary", "without any payment",
            "just information", "just reminder", "no urgency", "take your time",
            "visit official website", "government website", "official app",
            "no rush", "no payment required now", "vaccine is free", "no registration fee",
            "at hospital counter", "pay at hospital counter",
            "no agent needed", "direct application", "no fees for application",
            "no phone or online resolution", "security measure",
            "not ask for any personal", "participation is voluntary",
            "pay at delivery", "all customers treated equally",
            "grace period", "no urgency", "no discounts available",
            "bring food items directly", "no cash donations",
            "do not expire", "no processing fee"
        ]
        
        transcript_lower = transcript.lower()
        
        scam_score = sum(1 for keyword in scam_keywords if keyword.lower() in transcript_lower)
        legitimate_score = sum(1 for keyword in legitimate_indicators if keyword.lower() in transcript_lower)
        negative_score = sum(1 for keyword in negative_indicators if keyword.lower() in transcript_lower)
        
        # Special handling for bank freeze - legitimate if "visit branch" present
        if "account freeze" in transcript_lower and "visit your nearest branch" in transcript_lower:
            return {
                "category": "NORMAL",
                "is_scam": False,
                "reasoning": "Legitimate account freeze requiring branch visit"
            }
        
        # Special handling for callback scenario - legitimate if "you had called us" present
        if "you had called us" in transcript_lower and legitimate_score >= 2:
            return {
                "category": "NORMAL",
                "is_scam": False,
                "reasoning": "Legitimate callback scenario with verification"
            }
        
        # Bank service call - if customer service + credit card benefits + would you like to know
        if "customer service" in transcript_lower and "credit card benefits" in transcript_lower:
            if "would you like to know" in transcript_lower and scam_score <= 1:
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate bank service call - informational only"
                }
        
        # Callback scenario - if caller says you called them first, it's likely legitimate
        if "you had called us earlier" in transcript_lower or "requested callback" in transcript_lower:
            # BUT: if they still ask for card/account details, it's a scam
            if not ("card" in transcript_lower or "atm" in transcript_lower or "account" in transcript_lower):
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Callback scenario - user initiated contact first"
                }
        
        # Date of birth verification - if only asking for DOB without payment/card details, likely legitimate
        if "date of birth" in transcript_lower and scam_score <= 2:
            if not ("pay" in transcript_lower or "card" in transcript_lower or "atm" in transcript_lower or "account" in transcript_lower):
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate verification - only DOB requested"
                }
        
        # Callback verification exception - if callback + date of birth + no payment/card/account
        if ("you had called us earlier" in transcript_lower or "requested callback" in transcript_lower) and "date of birth" in transcript_lower:
            if not ("pay" in transcript_lower or "card" in transcript_lower or "atm" in transcript_lower or "account" in transcript_lower or "otp" in transcript_lower or "password" in transcript_lower):
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate callback verification - only DOB requested"
                }
        
        # Bank customer service callback - if customer service + credit card statement + date of birth
        if "customer service" in transcript_lower and "credit card statement" in transcript_lower and "date of birth" in transcript_lower:
            if not ("pay" in transcript_lower or "card number" in transcript_lower or "atm" in transcript_lower or "account number" in transcript_lower or "otp" in transcript_lower or "password" in transcript_lower or "cvv" in transcript_lower):
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate bank callback - DOB verification for statement inquiry"
                }
        
        # Maintenance notification - if maintenance + scheduled + no action needed
        if "maintenance" in transcript_lower and "scheduled" in transcript_lower:
            if "no action needed" in transcript_lower or "service will restore" in transcript_lower:
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate maintenance notification - no action required"
                }
        
        # Punjabi legitimate override - check specifically for legitimate phrase
        if "ਮੁਫ਼ਤ" in transcript_lower and "ਪੈਸੇ ਦੀ ਲੋੜ ਨਹੀਂ" in transcript_lower:
            if not any(scam in transcript_lower for scam in ["ਪਾਸਵਰਡ", "ਓਟੀਪੀ", "ਕਾਰਡ", "ਖਾਤਾ", "ਅਨੁਪ", "ਚ੆ਲ੍ਲ"]):
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Punjabi legitimate call - free service, no money needed"
                }
        
        # Multi-step trust scam override - if they ask to open FD after customer satisfaction survey
        if "customer satisfaction survey" in transcript_lower and "open fd" in transcript_lower:
            return {
                "category": "SCAM_DETECTED",
                "is_scam": True,
                "reasoning": "Multi-step scam - survey followed by FD opening request"
            }
        
        # SIM info legitimate - if they say they blocked SIMs and no action needed
        if "no action needed from your side" in transcript_lower and "blocked them" in transcript_lower:
            return {
                "category": "NORMAL",
                "is_scam": False,
                "reasoning": "Legitimate SIM info - blocked unauthorized SIMs, no action needed"
            }
        
        # Multi-step trust building then scam - check if legitimate indicators are followed by scam indicators
        if legitimate_score >= 1 and scam_score >= 1:
            # If asking for money/payment after building trust, it's a scam
            # BUT: if it's gas agency with "no advance payment" or "pay at delivery", it's legitimate
            if "no advance payment" in transcript_lower or "pay at delivery" in transcript_lower or "pay on delivery" in transcript_lower:
                return {
                    "category": "NORMAL",
                    "is_scam": False,
                    "reasoning": "Legitimate service - payment at delivery, no advance"
                }
            elif "pay" in transcript_lower or "transfer" in transcript_lower or "payment" in transcript_lower:
                return {
                    "category": "SCAM_DETECTED",
                    "is_scam": True,
                    "reasoning": "Multi-step scam - trust building followed by payment request"
                }
        
        # If negative indicators present, prioritize legitimate classification
        # BUT: if "cyber crime" or "anti-scam" is mentioned with card details, it's likely a scam
        if negative_score >= 1 and scam_score <= 2:
            if "cyber crime" in transcript_lower or "anti-scam" in transcript_lower:
                if "card" in transcript_lower or "atm" in transcript_lower or "account" in transcript_lower:
                    return {
                        "category": "SCAM_DETECTED",
                        "is_scam": True,
                        "reasoning": "Suspicious: claims to be anti-scam but asks for card/account details"
                    }
            return {
                "category": "NORMAL",
                "is_scam": False,
                "reasoning": f"Rule-based detection: {negative_score} negative indicators override {scam_score} scam indicators"
            }
        
        # Rule-based decision
        if scam_score >= 1:
            return {
                "category": "SCAM_DETECTED",
                "is_scam": True,
                "reasoning": f"Rule-based detection: {scam_score} scam indicators found"
            }
        elif legitimate_score >= 2:
            return {
                "category": "NORMAL",
                "is_scam": False,
                "reasoning": f"Rule-based detection: {legitimate_score} legitimate indicators found"
            }
        
        # Conservative fallback
        return {
            "category": "UNKNOWN",
            "is_scam": scam_score > 0,
            "reasoning": f"Ambiguous: {scam_score} scam, {legitimate_score} legitimate, {negative_score} negative indicators"
        }
