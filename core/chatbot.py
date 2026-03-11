"""
Chatbot logic for client-admin communication
Handles inquiry routing, pricing negotiation, and project clarification
"""

class ChatbotResponses:
    """Predefined chatbot responses for common inquiries"""
    
    GREETING = """
    Hello! I'm the ShadowIQ assistant. I'm here to help you with your research project.
    
    How can I assist you today? You can ask about:
    - Project pricing and timeline
    - Supported analysis types
    - Data requirements
    - Deliverables and reproducibility
    - General questions about our process
    """
    
    PRICING_INQUIRY = """
    Great question about pricing! Our rates depend on the complexity and scope of your project.
    
    Typical pricing ranges:
    - Sample size calculations: $200-$500
    - Statistical analysis: $500-$2,000
    - Full project support: $1,000-$5,000+
    - Data cleaning & preparation: $300-$1,500
    
    To provide an accurate quote, I'd like to know more about your project:
    1. What type of analysis do you need?
    2. How large is your dataset?
    3. What's your timeline?
    
    Would you like to discuss your specific project needs?
    """
    
    TIMELINE_INQUIRY = """
    Our typical timelines are:
    - Simple analyses: 3-5 business days
    - Standard projects: 1-2 weeks
    - Complex projects: 2-4 weeks
    
    Rush projects may be available at a premium rate. What's your deadline?
    """
    
    DELIVERABLES_INFO = """
    Every ShadowIQ project includes:
    
    1. **PDF Report** - Clear methods, results, interpretation, and limitations
    2. **Reproducible Notebook** - Jupyter or RMarkdown with full code
    3. **Code Bundle** - Scripts, requirements file, and README
    4. **Data Processing Log** - Documentation of all cleaning steps
    5. **QA Report** - Reproducibility and plagiarism checks
    6. **Statement of Work** - Signed contract with scope and terms
    
    All deliverables are designed for reproducibility and verification.
    """
    
    DATA_REQUIREMENTS = """
    Data requirements depend on your analysis type:
    
    **Accepted formats:**
    - CSV, Excel (XLSX, XLS)
    - JSON, XML
    - SQL database exports
    - Stata, SPSS, R data files
    - Text files with structured data
    
    **Data should be:**
    - De-identified (no personal information)
    - Properly formatted with clear variable names
    - Include data dictionary if available
    
    **Maximum file size:** 500 MB for MVP
    
    Do you have questions about preparing your data?
    """
    
    COMPLIANCE_INFO = """
    ShadowIQ takes compliance seriously:
    
    ✓ **Privacy First** - Minimal PII storage, pseudonymous accounts
    ✓ **Ethical Safeguards** - Strict policies against academic fraud
    ✓ **IRB Compliance** - We require IRB approval for human subjects research
    ✓ **Data Security** - Encrypted storage, secure file transfers
    ✓ **Audit Trails** - Complete logging for accountability
    
    All projects must comply with our Acceptable Use Policy. Do you have specific compliance questions?
    """
    
    NEXT_STEPS = """
    Here's how to move forward:
    
    1. **Submit Your Project** - Fill out our intake form with project details
    2. **Initial Review** - Our team reviews your submission (24-48 hours)
    3. **Pricing Discussion** - We'll provide a quote and timeline
    4. **Agreement** - Sign the Statement of Work
    5. **Payment** - Secure payment via Stripe (escrow for larger projects)
    6. **Analysis** - Our analyst begins work
    7. **QA Review** - Reproducibility and quality checks
    8. **Delivery** - Download your complete deliverable package
    
    Ready to submit your project?
    """
    
    @staticmethod
    def get_response(inquiry_type):
        """Get chatbot response based on inquiry type"""
        responses = {
            'greeting': ChatbotResponses.GREETING,
            'pricing': ChatbotResponses.PRICING_INQUIRY,
            'timeline': ChatbotResponses.TIMELINE_INQUIRY,
            'deliverables': ChatbotResponses.DELIVERABLES_INFO,
            'data': ChatbotResponses.DATA_REQUIREMENTS,
            'compliance': ChatbotResponses.COMPLIANCE_INFO,
            'next_steps': ChatbotResponses.NEXT_STEPS,
        }
        return responses.get(inquiry_type, ChatbotResponses.GREETING)

class InquiryClassifier:
    """Classify user inquiries to route to appropriate responses"""
    
    KEYWORDS = {
        'pricing': ['price', 'cost', 'fee', 'quote', 'budget', 'how much', 'expensive'],
        'timeline': ['timeline', 'how long', 'deadline', 'rush', 'urgent', 'fast', 'quick'],
        'deliverables': ['deliverable', 'output', 'what do i get', 'notebook', 'report', 'code'],
        'data': ['data', 'format', 'file', 'upload', 'dataset', 'csv', 'excel', 'requirements'],
        'compliance': ['compliance', 'irb', 'ethics', 'privacy', 'security', 'legal', 'hipaa'],
        'next_steps': ['next', 'how do i', 'process', 'submit', 'start', 'begin'],
    }
    
    @staticmethod
    def classify(message):
        """Classify inquiry and return category"""
        message_lower = message.lower()
        
        for category, keywords in InquiryClassifier.KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return category
        
        return 'greeting'
