"""Standardized skill dictionary.

Each entry has:
  name     canonical name shown to the user
  category used for scoring and display
  aliases  phrasings that mean the same skill (synonym matches)
  related  skills that are relevant but NOT the same (related-skill matches)
  implies  skills a confirmed mention lets us infer (partial matches)
  hints    descriptive phrases that suggest the skill without naming it
           (treated as inferred evidence, never as confirmation)

In a later stage this moves to the `keyword_dictionary` table so admins can
extend it without a deploy.
"""

from __future__ import annotations

from dataclasses import dataclass

TECHNICAL_CATEGORIES = {
    "programming", "framework", "database", "cloud", "devops", "testing",
    "networking", "security", "data", "tools", "mobile", "web",
}
QUALIFICATION_CATEGORIES = {"certification", "language"}
SOFT_CATEGORY = "soft_skill"


@dataclass(frozen=True)
class SkillDef:
    name: str
    category: str
    aliases: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    implies: tuple[str, ...] = ()
    hints: tuple[str, ...] = ()

    @property
    def all_aliases(self) -> tuple[str, ...]:
        return (self.name.lower(), *(a.lower() for a in self.aliases))


def S(name, category, aliases=(), related=(), implies=(), hints=()):
    return SkillDef(name, category, tuple(aliases), tuple(related), tuple(implies), tuple(hints))


SKILLS: list[SkillDef] = [
    # ---- programming languages
    S("Python", "programming", ["python3"]),
    S("Java", "programming", ["core java", "java se", "java ee"], related=["Kotlin"]),
    S("JavaScript", "programming", ["js", "ecmascript", "es6"], related=["TypeScript"]),
    S("TypeScript", "programming", [], related=["JavaScript"], implies=["JavaScript"]),
    S("C++", "programming", ["cpp"]),
    S("C#", "programming", ["c sharp", "csharp"], related=[".NET"]),
    S("Dart", "programming", [], related=["Flutter"]),
    S("Kotlin", "programming", [], related=["Java"]),
    S("Swift", "programming", []),
    S("PHP", "programming", []),
    S("Go (Golang)", "programming", ["golang"]),
    S("SQL", "programming", ["t-sql", "pl/sql", "sql queries"]),
    S("HTML", "web", ["html5"]),
    S("CSS", "web", ["css3"], related=["Tailwind CSS"]),
    # ---- frameworks
    S("React", "framework", ["react.js", "reactjs", "react js"], related=["Angular", "Vue.js"], implies=["JavaScript"]),
    S("Angular", "framework", ["angularjs"], related=["React", "Vue.js"], implies=["TypeScript"]),
    S("Vue.js", "framework", ["vue", "vuejs"], related=["React", "Angular"], implies=["JavaScript"]),
    S("Node.js", "framework", ["node", "nodejs", "node js"], related=["Express"], implies=["JavaScript"]),
    S("Express", "framework", ["express.js", "expressjs"], implies=["Node.js"]),
    S("Spring Boot", "framework", ["spring", "spring framework"], implies=["Java"]),
    S("Django", "framework", [], related=["Flask", "FastAPI"], implies=["Python"]),
    S("Flask", "framework", [], related=["Django", "FastAPI"], implies=["Python"]),
    S("FastAPI", "framework", [], related=["Django", "Flask"], implies=["Python", "REST APIs"]),
    S(".NET", "framework", ["dotnet", "asp.net", ".net core"], related=["C#"]),
    S("Tailwind CSS", "framework", ["tailwind"], implies=["CSS"]),
    S("Flutter", "mobile", [], related=["React Native"], implies=["Dart", "Mobile development"]),
    S("React Native", "mobile", [], related=["Flutter"], implies=["Mobile development", "JavaScript"]),
    S("Mobile development", "mobile", ["mobile applications", "mobile apps", "mobile app development",
                                       "cross-platform mobile", "android development", "ios development"]),
    S("REST APIs", "web", ["rest api", "rest apis", "restful", "restful api", "restful apis",
                           "restful services", "rest services", "restful web services"],
      related=["GraphQL"]),
    S("GraphQL", "web", [], related=["REST APIs"]),
    # ---- databases
    S("PostgreSQL", "database", ["postgres", "postgresql"], related=["MySQL", "SQL Server"],
      implies=["SQL", "Relational databases"]),
    S("MySQL", "database", [], related=["PostgreSQL", "SQL Server"], implies=["SQL", "Relational databases"]),
    S("SQL Server", "database", ["mssql", "microsoft sql server"], related=["PostgreSQL", "MySQL"],
      implies=["SQL", "Relational databases"]),
    S("MongoDB", "database", ["mongo"], related=["NoSQL"]),
    S("Redis", "database", []),
    S("Relational databases", "database", ["relational database", "rdbms"], related=["SQL"]),
    S("NoSQL", "database", [], related=["MongoDB"]),
    # ---- cloud / devops
    S("AWS", "cloud", ["amazon web services", "ec2", "s3", "aws lambda"], related=["Azure", "Google Cloud"],
      implies=["Cloud computing"]),
    S("Azure", "cloud", ["microsoft azure"], related=["AWS", "Google Cloud"], implies=["Cloud computing"]),
    S("Google Cloud", "cloud", ["gcp", "google cloud platform"], related=["AWS", "Azure"], implies=["Cloud computing"]),
    S("Cloud computing", "cloud", ["cloud deployment", "cloud services", "cloud infrastructure"]),
    S("Docker", "devops", ["docker compose", "containerization", "containers"], related=["Kubernetes"]),
    S("Kubernetes", "devops", ["k8s"], related=["Docker"]),
    S("CI/CD", "devops", ["ci/cd pipelines", "continuous integration", "continuous delivery",
                          "continuous deployment", "github actions", "jenkins"]),
    S("Git", "devops", ["version control"], related=["GitHub"]),
    S("GitHub", "devops", [], implies=["Git"]),
    S("Linux", "devops", ["ubuntu", "unix"]),
    # ---- testing
    S("Software testing", "testing", ["automated testing", "automated tests", "test automation",
                                      "quality assurance", "qa testing"], related=["Unit testing"]),
    S("Unit testing", "testing", ["unit tests", "unit test"], implies=["Software testing"]),
    S("JUnit", "testing", [], implies=["Unit testing", "Java"]),
    S("Pytest", "testing", [], implies=["Unit testing", "Python"]),
    S("Selenium", "testing", [], implies=["Software testing"]),
    # ---- methodologies / project management
    S("Agile", "methodology", ["agile development", "agile methodology", "agile methodologies"], related=["Scrum"]),
    S("Scrum", "methodology", ["sprint planning", "daily standups"], implies=["Agile"]),
    S("DevOps", "methodology", [], related=["CI/CD"]),
    S("Project management", "project_management", ["managed projects", "project coordination"],
      related=["Stakeholder management"]),
    S("Stakeholder management", "project_management", ["stakeholder communication", "stakeholders"]),
    S("Jira", "tools", [], related=["Asana", "Trello"]),
    S("Asana", "tools", [], related=["Jira", "Trello"]),
    S("Trello", "tools", [], related=["Jira", "Asana"]),
    # ---- networking / IT support / security
    S("TCP/IP", "networking", ["tcp ip"], implies=["Networking"]),
    S("DNS", "networking", [], implies=["Networking"]),
    S("VPN", "networking", [], implies=["Networking"]),
    S("Networking", "networking", ["network administration", "lan/wan", "network configuration"]),
    S("Troubleshooting", "it_support", ["troubleshoot", "troubleshot", "technical troubleshooting"],
      hints=["resolved technical", "technical problems", "technical issues", "diagnosed"]),
    S("Help desk", "it_support", ["helpdesk", "service desk", "it support", "technical support", "tech support"],
      related=["Customer service"]),
    S("Active Directory", "it_support", [], related=["Windows Server"]),
    S("Windows Server", "it_support", [], related=["Active Directory"]),
    S("Ticketing systems", "tools", ["ticketing system", "ticketing", "support tickets", "tickets"],
      related=["Zendesk", "Freshdesk"]),
    S("Zendesk", "tools", [], related=["Freshdesk"], implies=["Ticketing systems"]),
    S("Freshdesk", "tools", [], related=["Zendesk"], implies=["Ticketing systems"]),
    S("Cybersecurity", "security", ["information security", "infosec", "cyber security"]),
    S("SIEM", "security", ["splunk"], implies=["Cybersecurity"]),
    S("Firewalls", "security", ["firewall"], implies=["Networking"]),
    # ---- data
    S("Excel", "data", ["microsoft excel", "ms excel", "spreadsheets", "vlookup", "pivot tables"],
      related=["Google Workspace"]),
    S("Power BI", "data", ["powerbi"], related=["Tableau"], implies=["Data visualization"]),
    S("Tableau", "data", [], related=["Power BI"], implies=["Data visualization"]),
    S("Data visualization", "data", ["dashboards", "data visualisation"]),
    S("Data analysis", "data", ["data analytics", "analyzed data", "analysing data", "analyzing data"]),
    S("Machine learning", "data", ["ml models", "scikit-learn"]),
    # ---- office / admin
    S("Microsoft Office", "admin", ["ms office", "microsoft 365", "office 365", "microsoft word", "ms word",
                                    "outlook", "powerpoint"], related=["Google Workspace"]),
    S("Google Workspace", "admin", ["g suite", "gsuite", "google docs", "google sheets", "gmail",
                                    "google calendar"], related=["Microsoft Office"]),
    S("Data entry", "admin", ["data input", "entered data", "entering data"]),
    S("Calendar management", "admin", ["managed calendars", "calendar scheduling", "manage calendars",
                                       "managing calendars"], related=["Scheduling"]),
    S("Scheduling", "admin", ["schedule", "scheduled", "scheduling appointments"],
      related=["Appointment setting", "Calendar management"]),
    S("Email management", "admin", ["inbox management", "managed inbox", "email correspondence",
                                    "managing emails", "manage emails", "managed emails"]),
    S("Document management", "admin", ["filing", "document organization", "records management"]),
    # ---- customer service / contact centre
    S("Customer service", "customer_service", ["customer support", "customer care", "client support",
                                               "customer experience", "client services"],
      related=["Help desk"], hints=["customer calls", "customer inquiries", "customer questions", "assisted customers",
                                    "helped customers", "customers"]),
    S("Inbound calls", "customer_service", ["inbound calling", "inbound call", "inbound customer calls",
                                            "answered calls", "answering calls", "inbound"],
      related=["Outbound calls"], implies=["Phone support"]),
    S("Outbound calls", "sales", ["outbound calling", "outbound call", "outbound"],
      related=["Inbound calls", "Cold calling"], implies=["Phone support"]),
    S("Phone support", "customer_service", ["phone communication", "telephone support", "call handling",
                                            "phone calls", "calls", "call center", "call centre",
                                            "contact center", "contact centre"],
      related=["Customer service"]),
    S("Complaint resolution", "customer_service", ["complaints", "handled complaints", "resolve complaints",
                                                   "resolving complaints"],
      related=["De-escalation", "Escalation"]),
    S("Escalation", "customer_service", ["escalate", "escalated", "escalates", "escalating", "escalations",
                                         "escalate issues", "escalated issues"],
      related=["Complaint resolution"]),
    S("De-escalation", "customer_service", ["de-escalate", "de-escalated", "de-escalating", "upset customers",
                                            "angry customers", "frustrated customers", "difficult customers",
                                            "difficult callers", "frustrated callers"],
      related=["Complaint resolution"]),
    S("Refunds and returns", "customer_service", ["refund", "refunds", "refund requests", "returns",
                                                  "cancellations", "cancellation requests"],
      related=["Chargebacks"]),
    S("Chargebacks", "customer_service", ["chargeback", "payment disputes", "dispute responses",
                                          "dispute management"], related=["Refunds and returns"]),
    S("Review responses", "marketing", ["review management", "reputation management", "online reviews"]),
    S("Call notes", "customer_service", ["call outcomes", "call notes", "documented calls", "case notes",
                                         "accurate notes", "documentation", "record important details",
                                         "record details", "recorded details", "record call outcomes",
                                         "accurate records", "taking notes", "take notes", "notes"],
      related=["CRM"]),
    S("Call scripts", "customer_service", ["scripts", "script", "call script", "campaign scripts"]),
    S("Quality standards", "customer_service", ["quality metrics", "quality assurance scores", "kpis", "metrics",
                                                "quality scores", "csat"]),
    # ---- sales / business development
    S("Cold calling", "sales", ["cold call", "cold calls", "cold-calling", "cold-call"], related=["Outbound calls"],
      implies=["Outbound calls"]),
    S("Appointment setting", "sales", ["appointment setter", "setting appointments", "booking appointments",
                                       "book appointments", "booked appointments", "schedule appointments",
                                       "booked meetings", "booking meetings", "book meetings", "book qualified meetings",
                                       "meetings booked"], related=["Scheduling"], implies=["Scheduling"]),
    S("Lead generation", "sales", ["lead gen", "generating leads", "generated leads", "generate leads",
                                   "prospecting", "outbound prospecting"], related=["Lead qualification"]),
    S("Lead qualification", "sales", ["qualify leads", "qualifying leads", "qualified leads", "qualify prospects",
                                      "qualified prospects", "qualified potential customers",
                                      "qualify interested customers", "qualifying customers"],
      related=["Lead generation"]),
    S("Objection handling", "sales", ["handle objections", "handling objections", "handled objections",
                                      "overcome objections", "overcoming objections", "objections"]),
    S("Sales", "sales", ["inside sales", "b2c sales", "sales calls", "sales experience", "selling"],
      related=["B2B sales"]),
    S("B2B sales", "sales", ["b2b", "business-to-business"], related=["Sales"]),
    S("Pipeline management", "sales", ["sales pipeline", "pipeline"], related=["CRM"]),
    S("Follow-up", "sales", ["follow up", "follow-ups", "follow ups", "followed up", "following up"]),
    S("CRM", "tools", ["crm system", "crm software", "customer relationship management"],
      related=["Call notes"]),
    S("Salesforce", "tools", [], related=["HubSpot"], implies=["CRM"]),
    S("HubSpot", "tools", [], related=["Salesforce"], implies=["CRM"]),
    S("LinkedIn prospecting", "sales", ["linkedin outreach", "linkedin sales navigator", "sales navigator",
                                        "linkedin prospecting"], related=["Lead generation"]),
    S("Cold email", "sales", ["cold emails", "cold emailing", "email outreach", "email campaigns"],
      related=["Lead generation"]),
    S("Shopify", "tools", [], related=["E-commerce"], implies=["E-commerce"]),
    S("E-commerce", "tools", ["ecommerce", "online stores", "online store"]),
    S("Stripe", "tools", [], related=["PayPal"], implies=["Payment processors"]),
    S("PayPal", "tools", [], related=["Stripe"], implies=["Payment processors"]),
    S("Payment processors", "tools", ["payment processor", "payment processing"]),
    # ---- marketing
    S("SEO", "marketing", ["search engine optimization"], related=["Content marketing"]),
    S("Social media marketing", "marketing", ["social media", "social media management"]),
    S("Content marketing", "marketing", ["content creation", "copywriting"], related=["SEO"]),
    S("Google Analytics", "marketing", ["ga4"], implies=["Data analysis"]),
    # ---- HR
    S("Recruiting", "hr", ["recruitment", "talent acquisition", "sourcing candidates"], related=["Onboarding"]),
    S("Onboarding", "hr", ["employee onboarding"], related=["Recruiting"]),
    S("Payroll", "hr", ["payroll processing"]),
    # ---- finance / banking
    S("Accounting", "finance", ["general ledger", "reconciliations", "account reconciliation"],
      related=["Bookkeeping"]),
    S("Bookkeeping", "finance", [], related=["Accounting"]),
    S("QuickBooks", "finance", [], implies=["Bookkeeping"]),
    S("Financial analysis", "finance", ["financial modeling", "financial modelling", "forecasting"]),
    S("Accounts payable", "finance", ["a/p"], related=["Accounts receivable"]),
    S("Accounts receivable", "finance", ["a/r", "collections"], related=["Accounts payable"]),
    # ---- healthcare admin
    S("Medical billing", "healthcare_admin", ["medical coding", "insurance billing"]),
    S("HIPAA", "healthcare_admin", ["hipaa compliance"]),
    S("EHR", "healthcare_admin", ["electronic health records", "emr", "electronic medical records"]),
    # ---- certifications
    S("AWS Certified Cloud Practitioner", "certification", ["aws cloud practitioner"], implies=["AWS"]),
    S("CCNA", "certification", ["cisco certified network associate"], implies=["Networking"]),
    S("CompTIA A+", "certification", ["comptia a+", "a+ certification", "a+ certified"]),
    S("CompTIA Security+", "certification", ["security+"], implies=["Cybersecurity"]),
    S("PMP", "certification", ["project management professional"], implies=["Project management"]),
    S("CPA", "certification", ["certified public accountant"], implies=["Accounting"]),
    S("Certified ScrumMaster", "certification", ["csm", "scrum master certification", "certified scrum master"],
      implies=["Scrum"]),
    # ---- spoken languages
    S("English", "language", ["english language", "fluent english", "native english"]),
    S("Spanish", "language", ["bilingual spanish"]),
    S("French", "language", []),
    S("Amharic", "language", []),
    # ---- soft skills
    S("Communication", "soft_skill", ["communication skills", "communicate", "communicating", "communicates",
                                      "communicator", "verbal communication", "written communication",
                                      "communicate clearly", "speaks clearly", "speak clearly"]),
    S("Active listening", "soft_skill", ["listening", "listen", "listens", "listener"]),
    S("Problem-solving", "soft_skill", ["problem solving", "solve problems", "solving problems", "problem solver"],
      related=["Troubleshooting"]),
    S("Leadership", "soft_skill", ["led a team", "team lead", "mentored", "supervised"]),
    S("Teamwork", "soft_skill", ["team collaboration", "collaboration", "collaborated", "collaborative",
                                 "team player", "cross-functional"]),
    S("Time management", "soft_skill", ["prioritization", "prioritize", "deadlines"]),
    S("Attention to detail", "soft_skill", ["detail-oriented", "detail oriented", "accuracy", "accurate"]),
    S("Adaptability", "soft_skill", ["adaptable", "flexible", "learns quickly", "learn quickly", "quick learner",
                                     "learn new tools", "fast learner"]),
    S("Organization", "soft_skill", ["organized", "organised", "organizational skills", "organisational skills"]),
    S("Reliability", "soft_skill", ["reliable", "dependable", "consistent", "punctual"]),
    S("Professionalism", "soft_skill", ["professional", "professionally", "polite", "courteous"]),
    S("Patience", "soft_skill", ["patient", "calm under pressure", "stay calm", "stays calm", "remain calm",
                                 "calmly", "calm", "calmed", "stayed calm"]),
    S("Empathy", "soft_skill", ["empathetic", "empathize"]),
    S("Independent work", "soft_skill", ["work independently", "works independently", "self-motivated",
                                         "without supervision", "self-starter"]),
]

SKILLS_BY_NAME: dict[str, SkillDef] = {s.name: s for s in SKILLS}


def _validate() -> None:
    for s in SKILLS:
        for ref in (*s.related, *s.implies):
            if ref not in SKILLS_BY_NAME:
                raise ValueError(f"{s.name!r} references unknown skill {ref!r}")


_validate()
