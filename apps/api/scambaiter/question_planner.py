"""
scambaiter/question_planner.py — Intelligent question planner for Scambaiter.

Purpose:
  Analyze scammer's statements and generate strategic questions to extract
  incriminating information for the forensic PDF dossier.

Goals:
  1. Identify information gaps from scammer's statements
  2. Generate targeted questions to extract:
     - Company names
     - Phone numbers
     - Website URLs
     - Bank account details
  3. Avoid repetitive questions
  4. Maintain the elderly persona while being inquisitive
  5. Track extracted evidence for dossier generation
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Single piece of evidence extracted from scammer."""
    category: str  # company, phone, website, bank, upi, scheme, threat
    value: str
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""  # Surrounding conversation context


@dataclass
class ScammerProfile:
    """Profile of the scammer built from conversation."""
    company_name: Optional[str] = None
    phone_numbers: List[str] = field(default_factory=list)
    websites: List[str] = field(default_factory=list)
    bank_accounts: List[str] = field(default_factory=list)
    upi_ids: List[str] = field(default_factory=list)
    schemes_offered: List[str] = field(default_factory=list)
    threats_made: List[str] = field(default_factory=list)
    personal_info: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # Overall confidence in profile


class QuestionPlanner:
    """Generates strategic questions to extract scammer information."""

    # Patterns for detecting information in scammer speech
    PATTERNS = {
        "company": [
            r"\b(?:company|organization|firm|ltd|pvt|limited|corporation|enterprise)\b",
            r"\b(?:SBI|HDFC|ICICI|Axis|PNB|LIC|Bajaj|Reliance|Tata|Adani)\b",
            r"\b(?:Pradhan Mantri|PM|government|gov|ministry)\b",
            r"\b(?:RBI|SEBI|IRDA|TRAI)\b",  # Regulatory bodies
            r"\b(?:NPCI|UPI|BHIM)\b",  # Payment systems
        ],
        "phone": [
            r"\b\d{10}\b",  # 10-digit mobile
            r"\b\d{11,12}\b",  # Phone with country code
            r"\b(?:toll.?free|customer.?care|helpline)\b",
            r"\b(?:mobile|contact|call)\s*\d+",
        ],
        "website": [
            r"\b(?:https?://|www\.|\.com|\.in|\.org)\b",
            r"\b(?:portal|website|link|url|download)\b",
            r"\b(?:app|application)\s*(?:download|install)\b",
        ],
        "bank": [
            r"\b(?:account|bank|IFSC|branch|MICR)\b",
            r"\b(?:deposit|transfer|withdraw|credit|debit)\b",
            r"\b(?:savings|current|FD|RD)\s*account\b",
            r"\b(?:cheque|check|NEFT|RTGS|IMPS)\b",
        ],
        "upi": [
            r"\b(?:UPI|GPay|Paytm|PhonePe|BHIM)\b",
            r"\b[\w.\-]+@[\w]+\.(?:upi|apl)\b",
            r"\b(?:QR code|QR)\b",
            r"\b(?:payment|pay|send money)\b",
        ],
        "scheme": [
            r"\b(?:scheme|plan|offer|discount|bonus|reward|prize|lottery)\b",
            r"\b(?:insurance|policy|investment|FD|RD|SIP|mutual fund)\b",
            r"\b(?:loan|credit card|personal loan|home loan)\b",
            r"\b(?:subsidy|benefit|yojana|welfare)\b",
        ],
        "threat": [
            r"\b(?:police|court|case|FIR|arrest|jail|legal action)\b",
            r"\b(?:block|suspend|freeze|deactivate|close)\b",
            r"\b(?:serious|consequence|trouble|problem|issue)\b",
            r"\b(?:action|penalty|fine|complaint)\b",
        ],
        "personal": [
            r"\b(?:name|age|dob|date of birth|address)\b",
            r"\b(?:father|mother|spouse|family)\b",
            r"\b(?:aadhaar|PAN|ID proof|identity)\b",
        ],
    }

    # Questions to ask based on missing information
    QUESTIONS = {
        "company": [
            "बेटा, आप किस कंपनी से बोल रहे हो?",
            "आपकी कंपनी का नाम क्या है?",
            "क्या यह सरकारी योजना है?",
            "कार्यालय कहाँ है?",
            "कंपनी का पता बताओ ना।",
        ],
        "phone": [
            "अगर मुझे बात करनी हो तो कौन से नंबर डालूं?",
            "आपका आधिकारिक नंबर क्या है?",
            "helpline नंबर बताओ ना बेटा।",
            "कस्टमर केयर का नंबर दो।",
            "क्या मैं आपको वापस कॉल कर सकता हूँ?",
        ],
        "website": [
            "वेबसाइट का पता बताओ ना, मैं देख लूंगा।",
            "क्या कोई लिंक भेजना है?",
            "website दिखाओ तो सही।",
            "ऐप कैसे डाउनलोड करूँ?",
            "और जानकारी कहाँ मिलेगी?",
        ],
        "bank": [
            "बैंक का नाम क्या है?",
            "IFSC कोड बताओ ना।",
            "अकाउंट नंबर क्या है?",
            "कौन सी ब्रांच है?",
            "बैंक का पता बताओ।",
        ],
        "upi": [
            "UPI ID बताओ ना बेटा।",
            "किस UPI पर भेजना है?",
            "GPay/Paytm का नंबर दो।",
            "QR code भेजोगे?",
            "payment कैसे करना है?",
        ],
        "scheme": [
            "यह कौन सा स्कीम है बेटा?",
            "इसमें क्या बेनिफिट है?",
            "प्रोसेस कैसे होगा?",
            "कितना मिलेगा?",
            "documents कौन से चाहिए?",
        ],
        "threat": [
            "क्या कोई दिक्कत है?",
            "क्या मेरा कनेक्शन बंद हो जाएगा?",
            "आप क्या कर दोगे?",
            "क्या पुलिस बुलाओगे?",
            "क्या कोई कानूनी कार्रवाई होगी?",
        ],
        "personal": [
            "मेरा नाम क्या है?",
            "मेरी उम्र क्या है?",
            "मेरा पता बताओ ना।",
            "मेरे पिता का नाम क्या है?",
            "मेरा Aadhaar नंबर बताओ।",
        ],
    }

    def __init__(self):
        self.profile = ScammerProfile()
        self.asked_questions: Dict[str, List[str]] = {
            key: [] for key in self.QUESTIONS.keys()
        }
        self.evidence_history: List[Evidence] = []
        self.priority_categories: List[str] = []  # Prioritized categories based on fact-check

    def set_priority_from_category(self, scam_category: str):
        """
        Set question priorities based on detected scam category.
        
        Different scam types have different information priorities.
        """
        # Mapping of scam categories to priority information categories
        category_priorities = {
            "UPI_COLLECT_FRAUD": ["upi", "phone", "company"],
            "GIFT_CARD_PAYMENT": ["scheme", "phone", "company"],
            "WIRE_TRANSFER_FRAUD": ["bank", "phone", "company"],
            "CRYPTO_SCAM": ["website", "scheme", "upi"],
            "SIM_SWAP": ["phone", "company", "personal"],
            "DIGITAL_ARREST": ["phone", "company", "threat"],
            "IMPERSONATION_LAW": ["phone", "company", "threat"],
            "KYC_SIM_BLOCK": ["phone", "company", "personal"],
            "ROMANCE_SCAM": ["website", "phone", "personal"],
            "FAMILY_EMERGENCY": ["phone", "personal", "threat"],
            "SEXTORTION": ["upi", "phone", "threat"],
            "INVESTMENT_FRAUD": ["website", "scheme", "bank"],
            "PRIZE_LOTTERY": ["scheme", "phone", "upi"],
            "TECH_SUPPORT": ["website", "phone", "company"],
            "ACCOUNT_SECURITY_ALERT": ["phone", "company", "personal"],
            "LOAN_HARASSMENT": ["phone", "company", "bank"],
            "ELECTRICITY_THREAT": ["phone", "company", "threat"],
            "COURIER_CUSTOMS": ["phone", "company", "scheme"],
            "FAKE_JOB_TASK": ["website", "scheme", "phone"],
            "GOVT_SCHEME_IMPERSONATION": ["scheme", "phone", "company"],
            "MATRIMONIAL_FRAUD": ["upi", "phone", "personal"],
            "PENSION_PF_SCAM": ["phone", "company", "personal"],
            "MEDICAL_INSURANCE_SCAM": ["phone", "company", "scheme"],
            "SCHOLARSHIP_SCAM": ["scheme", "phone", "website"],
            "EXAM_ADMISSION_SCAM": ["scheme", "phone", "website"],
            "LOAN_APP_HOOK": ["website", "phone", "upi"],
            "GAMING_BETTING_SCAM": ["website", "upi", "phone"],
            "HR_RECRUITER_SCAM": ["website", "phone", "company"],
            "INCOME_TAX_REFUND": ["phone", "company", "bank"],
            "EPF_WITHDRAWAL_SCAM": ["phone", "company", "personal"],
            "PROMOTION_TRANSFER_SCAM": ["phone", "company", "scheme"],
            "GST_COMPLIANCE_SCAM": ["phone", "company", "threat"],
            "FERTILIZER_SEED_SUBSIDY": ["scheme", "phone", "company"],
            "KISAN_CREDIT_CARD": ["scheme", "phone", "bank"],
            "MODELING_CASTING_SCAM": ["website", "phone", "personal"],
            "MARKETPLACE_QR_SCAM": ["upi", "phone", "website"],
            "TRAFFIC_CHALLAN_SCAM": ["phone", "company", "scheme"],
            "VACCINATION_HEALTH_SCHEME": ["scheme", "phone", "company"],
            "FAKE_CUSTOMER_CARE": ["phone", "company", "upi"],
            "RAILWAY_IRCTC_REFUND": ["phone", "company", "bank"],
            "ECOMMERCE_REFUND_SCAM": ["phone", "company", "upi"],
            "CREDIT_CARD_UPGRADE": ["phone", "company", "bank"],
        }
        
        self.priority_categories = category_priorities.get(scam_category, [])
        if self.priority_categories:
            logger.info("QuestionPlanner: Set priorities for %s: %s", scam_category, self.priority_categories)

    def analyze_scammer_speech(self, speech: str) -> List[Evidence]:
        """
        Analyze scammer's speech for evidence patterns.

        Returns list of detected evidence items.
        """
        detected = []
        speech_lower = speech.lower()

        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, speech, re.IGNORECASE)
                for match in matches:
                    # Clean and normalize the match
                    cleaned = match.strip()
                    if cleaned and len(cleaned) > 2:
                        evidence = Evidence(
                            category=category,
                            value=cleaned,
                            confidence=0.8,
                            context=speech
                        )
                        detected.append(evidence)
                        self._update_profile(evidence)

        return detected

    def _update_profile(self, evidence: Evidence):
        """Update scammer profile with new evidence."""
        if evidence.confidence < 0.5:
            return

        if evidence.category == "company" and evidence.value not in str(self.profile.company_name):
            self.profile.company_name = evidence.value
        elif evidence.category == "phone" and evidence.value not in self.profile.phone_numbers:
            self.profile.phone_numbers.append(evidence.value)
        elif evidence.category == "website" and evidence.value not in self.profile.websites:
            self.profile.websites.append(evidence.value)
        elif evidence.category == "bank" and evidence.value not in self.profile.bank_accounts:
            self.profile.bank_accounts.append(evidence.value)
        elif evidence.category == "upi" and evidence.value not in self.profile.upi_ids:
            self.profile.upi_ids.append(evidence.value)
        elif evidence.category == "scheme" and evidence.value not in self.profile.schemes_offered:
            self.profile.schemes_offered.append(evidence.value)
        elif evidence.category == "threat" and evidence.value not in self.profile.threats_made:
            self.profile.threats_made.append(evidence.value)
        elif evidence.category == "personal" and evidence.value not in self.profile.personal_info:
            self.profile.personal_info.append(evidence.value)

        # Update overall confidence
        total_fields = sum([
            1 if self.profile.company_name else 0,
            len(self.profile.phone_numbers),
            len(self.profile.websites),
            len(self.profile.bank_accounts),
            len(self.profile.upi_ids),
            len(self.profile.schemes_offered),
            len(self.profile.threats_made),
            len(self.profile.personal_info),
        ])
        self.profile.confidence_score = min(total_fields / 8.0, 1.0)

        self.evidence_history.append(evidence)

    def identify_missing_info(self) -> List[str]:
        """
        Identify which information categories are missing or incomplete.

        Returns list of category names that need more information.
        """
        missing = []

        if not self.profile.company_name:
            missing.append("company")
        if len(self.profile.phone_numbers) == 0:
            missing.append("phone")
        if len(self.profile.websites) == 0:
            missing.append("website")
        if len(self.profile.bank_accounts) == 0:
            missing.append("bank")
        if len(self.profile.upi_ids) == 0:
            missing.append("upi")
        if len(self.profile.schemes_offered) == 0:
            missing.append("scheme")
        if len(self.profile.threats_made) == 0:
            missing.append("threat")
        if len(self.profile.personal_info) == 0:
            missing.append("personal")

        return missing

    def generate_question(self, category: str) -> str:
        """
        Generate a strategic question for a specific category.

        Ensures no repetition by tracking asked questions.
        """
        available_questions = [
            q for q in self.QUESTIONS[category]
            if q not in self.asked_questions[category]
        ]

        if not available_questions:
            # All questions asked, generate a generic one
            return f"बेटा, {category} के बारे में और बताओ।"

        # Pick a question and mark as asked
        question = available_questions[0]
        self.asked_questions[category].append(question)
        return question

    def get_next_strategic_question(self, context: str) -> Optional[str]:
        """
        Get the next strategic question based on current context and missing info.

        Returns None if no question is appropriate.
        """
        # First, analyze current speech for evidence
        detected = self.analyze_scammer_speech(context)

        # Identify missing information
        missing = self.identify_missing_info()

        if not missing:
            # Profile is complete, return None
            return None

        # Use priority categories if set (from fact-check), otherwise use default priority
        if self.priority_categories:
            priority_order = self.priority_categories + [c for c in ["company", "phone", "bank", "upi", "website", "scheme", "threat", "personal"] if c not in self.priority_categories]
        else:
            # Default priority: company > phone > bank > upi > website > scheme > threat > personal
            priority_order = ["company", "phone", "bank", "upi", "website", "scheme", "threat", "personal"]

        for category in priority_order:
            if category in missing:
                # Check if we should ask about this category based on context
                if self._should_ask_about(category, context):
                    return self.generate_question(category)

        return None

    def _should_ask_about(self, category: str, context: str) -> bool:
        """
        Determine if we should ask about a category based on context.

        Returns True if appropriate to ask.
        """
        # Don't ask if context already mentions this category
        context_lower = context.lower()
        category_keywords = {
            "company": ["company", "kompni", "firm", "ltd", "sbi", "hdfc"],
            "phone": ["number", "mobile", "call", "dial", "phone"],
            "website": ["website", "link", "url", "portal", "www"],
            "bank": ["bank", "account", "ifsc", "branch", "deposit"],
            "upi": ["upi", "gpay", "paytm", "phonepe", "bhim"],
            "scheme": ["scheme", "plan", "offer", "discount", "bonus"],
            "threat": ["police", "court", "case", "arrest", "block"],
            "personal": ["name", "age", "dob", "address", "father", "aadhaar"],
        }

        if category in category_keywords:
            for keyword in category_keywords[category]:
                if keyword in context_lower:
                    return False

        # Don't ask if we've already asked 3+ questions about this category
        if len(self.asked_questions[category]) >= 3:
            return False

        return True

    def get_profile_summary(self) -> Dict:
        """
        Get a summary of the current scammer profile for dossier generation.
        """
        return {
            "company_name": self.profile.company_name,
            "phone_numbers": self.profile.phone_numbers,
            "websites": self.profile.websites,
            "bank_accounts": self.profile.bank_accounts,
            "upi_ids": self.profile.upi_ids,
            "schemes_offered": self.profile.schemes_offered,
            "threats_made": self.profile.threats_made,
            "personal_info": self.profile.personal_info,
            "confidence_score": self.profile.confidence_score,
            "evidence_count": len(self.evidence_history),
        }

    def reset(self):
        """Reset the planner for a new scammer conversation."""
        self.profile = ScammerProfile()
        self.asked_questions = {key: [] for key in self.QUESTIONS.keys()}
        self.evidence_history = []
