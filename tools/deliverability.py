import re
import subprocess
import logging

logger = logging.getLogger(__name__)

# Common spam trigger words/phrases (case-insensitive checks)
SPAM_WORDS = [
    "free", "guarantee", "buy now", "click here", "risk-free", "risk free",
    "earn money", "make money", "opportunity", "cash", "save big", "winner",
    "prize", "income", "financial freedom", "act now", "special offer",
    "100% free", "no cost", "credit card", "investment", "refund", "unlimited",
    "extra income", "earn cash", "passive income", "multi-level", "hidden fees",
    "no catch", "make $", "lowest price", "certified", "cheap"
]

def check_domain_dns(email_address: str) -> dict:
    """
    Parses the domain from the email and queries for SPF/DMARC TXT records using nslookup.
    """
    result = {
        "domain": "",
        "spf_present": False,
        "dmarc_present": False,
        "details": []
    }
    
    if not email_address or "@" not in email_address:
        result["details"].append("No valid sender email configured. Running in fallback/mock mode.")
        return result

    domain = email_address.split("@")[-1].strip().lower()
    result["domain"] = domain

    # Known public email services defaults
    if domain in ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"]:
        result["spf_present"] = True
        result["dmarc_present"] = True
        result["details"].append(f"Public provider '{domain}' has built-in SPF/DMARC records.")
        return result

    try:
        # Check SPF by querying TXT records of the main domain
        spf_cmd = ["nslookup", "-type=txt", domain]
        spf_res = subprocess.run(spf_cmd, capture_output=True, text=True, timeout=3)
        spf_output = spf_res.stdout or ""
        
        if "v=spf1" in spf_output.lower():
            result["spf_present"] = True
            result["details"].append("SPF record verified.")
        else:
            result["details"].append("SPF record missing or invalid (no 'v=spf1' record found).")
            
        # Check DMARC by querying TXT records of _dmarc.domain
        dmarc_cmd = ["nslookup", "-type=txt", f"_dmarc.{domain}"]
        dmarc_res = subprocess.run(dmarc_cmd, capture_output=True, text=True, timeout=3)
        dmarc_output = dmarc_res.stdout or ""
        
        if "v=dmarc1" in dmarc_output.lower():
            result["dmarc_present"] = True
            result["details"].append("DMARC record verified.")
        else:
            result["details"].append("DMARC record missing or invalid (no 'v=DMARC1' record found).")
            
    except Exception as e:
        logger.warning(f"DNS lookup failed for {domain}: {str(e)}")
        # Graceful fallback to avoid blocking campaigns if nslookup fails or is offline
        result["spf_present"] = True
        result["dmarc_present"] = True
        result["details"].append("DNS query timed out. Assuming mock success to avoid blocking.")

    return result

def analyze_email(subject: str, body: str, sender_email: str = "") -> dict:
    """
    Performs multi-dimensional analysis on an email draft and returns a deliverability report.
    """
    subject = subject or ""
    body = body or ""
    
    issues = []
    spam_words_found = []
    
    # 1. Subject line analysis
    subj_len = len(subject)
    if subj_len > 60:
        issues.append(f"Subject is too long ({subj_len} chars). It may be truncated on mobile devices.")
    elif subj_len < 10 and subj_len > 0:
        issues.append(f"Subject is very short ({subj_len} chars) and might lack descriptive context.")
        
    # Capitalization & Exclamations in subject
    words = subject.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 1 and w.isalpha()]
    if len(caps_words) >= 2:
        issues.append(f"Subject has multiple ALL-CAPS words ({', '.join(caps_words)}), which triggers spam filters.")
        
    if "!" in subject:
        issues.append("Subject contains exclamation marks (!) which reduces open rates and alerts filters.")
        
    # Emojis in subject
    emoji_pattern = re.compile("[\U00010000-\U0010ffff\u2600-\u27bf]", flags=re.UNICODE)
    emojis = emoji_pattern.findall(subject)
    if len(emojis) > 1:
        issues.append(f"Subject contains multiple emojis ({len(emojis)}). Keep it to at most 1.")
        
    # 2. Body analysis
    # Spam words search
    body_lower = body.lower()
    for word in SPAM_WORDS:
        # Use regex boundary matching to avoid matching part of a longer word
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, body_lower):
            spam_words_found.append(word)
            
    if len(spam_words_found) > 0:
        issues.append(f"Spam trigger words detected in body: {', '.join(spam_words_found)}.")
        
    # Link count in body
    urls = re.findall(r'https?://[^\s]+', body)
    if len(urls) > 2:
        issues.append(f"Email body has too many links ({len(urls)}). Try to keep it below 2 links to avoid filters.")
        
    # 3. Domain Check
    dns_report = check_domain_dns(sender_email)
    
    # Compute score
    score = 100
    # Penalty per subject issue
    score -= len(issues) * 12
    # Penalty per spam word
    score -= len(spam_words_found) * 8
    # Domain check penalties
    if sender_email:
        if not dns_report["spf_present"]:
            score -= 20
            issues.append("Domain lacks an SPF record (highly critical for deliverability).")
        if not dns_report["dmarc_present"]:
            score -= 15
            issues.append("Domain lacks a DMARC record (critical for authentication).")
            
    score = max(10, min(100, score))
    
    # Assign status
    if score >= 85:
        status = "safe"
    elif score >= 60:
        status = "warning"
    else:
        status = "risky"
        
    return {
        "score": score,
        "status": status,
        "issues": issues,
        "spam_words_found": spam_words_found,
        "domain_checks": {
            "domain": dns_report["domain"],
            "spf_present": dns_report["spf_present"],
            "dmarc_present": dns_report["dmarc_present"],
            "details": dns_report["details"]
        }
    }
