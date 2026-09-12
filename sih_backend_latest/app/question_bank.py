"""Original, project-specific adaptive question bank. Not a diagnostic instrument."""
from dataclasses import asdict, dataclass

VERSION = "2.0"
ALL_AGES = ("13-17", "18-24", "25-44", "45-59", "60+")
ADOLESCENT = ("13-17",)
YOUNG = ("18-24",)
WORKING_AGES = ("18-24", "25-44", "45-59")
ADULTS = ("25-44", "45-59")
OLDER = ("45-59", "60+")


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    domain: str
    age_groups: tuple[str, ...]
    response_type: str = "frequency_5"
    severity_weight: int = 2
    critical: bool = False
    reverse_scored: bool = False
    follow_up_for: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    core: bool = False

    def public(self):
        return asdict(self)


# Each tuple is: text, ages, response type, weight, critical, reverse, parents, tags, core.
# IDs are deliberately derived from this immutable v2 ordering. Append-only changes require
# a new questionnaire version so historical IDs retain their meaning.
SPECS = [
 # mood (8)
 ("Over the past two weeks, how often have you felt low or emotionally weighed down?",ALL_AGES,"frequency_5",3,False,False,(),("sadness",),True),
 ("Recently, how severe have periods of sadness felt when they appeared?",ALL_AGES,"severity_5",2,False,False,(),("sadness",),False),
 ("How often have things you usually enjoy felt less interesting?",ALL_AGES,"frequency_5",2,False,False,(),("interest",),False),
 ("How often has it been difficult to feel any positive emotion?",ALL_AGES,"frequency_5",2,False,False,(),("positive-emotion",),False),
 ("How often has your mood changed sharply within the same day?",ALL_AGES,"frequency_5",1,False,False,(),("mood-change",),False),
 ("Compared with your usual self, how much has your emotional wellbeing worsened recently?",ALL_AGES,"severity_5",3,False,False,(),("deterioration",),True),
 ("How often have you felt tearful or close to tears?",ALL_AGES,"frequency_5",1,False,False,(),("tearful",),False),
 ("How often have you felt emotionally numb or disconnected from your feelings?",ALL_AGES,"frequency_5",2,False,False,(),("numbness",),False),
 # anxiety (8)
 ("Over the past two weeks, how often have you felt worried or afraid?",ALL_AGES,"frequency_5",3,False,False,(),("worry",),True),
 ("How difficult has it been to settle your worries once they begin?",ALL_AGES,"severity_5",2,False,False,(),("worry-control",),False),
 ("How often have you expected that something bad might happen?",ALL_AGES,"frequency_5",2,False,False,(),("anticipation",),False),
 ("How often have you felt suddenly overwhelmed by fear?",ALL_AGES,"frequency_5",3,False,False,(),("fear",),False),
 ("How often have small uncertainties felt hard to tolerate?",ALL_AGES,"frequency_5",1,False,False,(),("uncertainty",),False),
 ("How often have worries about people you care about been hard to manage?",ALL_AGES,"frequency_5",2,False,False,(),("family-worry",),False),
 ("How severe has nervousness felt in situations you normally manage?",ALL_AGES,"severity_5",2,False,False,(),("nervousness",),False),
 ("How often have you needed reassurance to feel calmer?",ALL_AGES,"frequency_5",1,False,False,(),("reassurance",),False),
 # trauma (8)
 ("How often have unwanted memories of a frightening or harmful experience returned?",ALL_AGES,"frequency_5",3,False,False,(),("intrusion",),False),
 ("How often have distressing dreams been connected to something you experienced?",ALL_AGES,"frequency_5",2,False,False,(),("dreams",),False),
 ("How often have reminders made you feel as if a difficult experience were happening again?",ALL_AGES,"frequency_5",3,False,False,(),("re-experiencing",),False),
 ("How severe has emotional distress been when something reminded you of the experience?",ALL_AGES,"severity_5",3,False,False,(),("reminders",),False),
 ("How often have you blamed yourself for something harmful that happened?",ALL_AGES,"frequency_5",2,False,False,(),("self-blame",),False),
 ("How often have you felt detached from what is happening around you?",ALL_AGES,"frequency_5",2,False,False,(),("dissociation",),False),
 ("How often have you found it hard to remember parts of a stressful experience?",ALL_AGES,"frequency_5",1,False,False,(),("memory",),False),
 ("How often have reminders caused a strong physical reaction, such as shaking or a racing heart?",ALL_AGES,"frequency_5",2,False,False,(),("physical-reaction",),False),
 # sleep (6)
 ("Over the past two weeks, how often have you had difficulty falling asleep?",ALL_AGES,"frequency_5",2,False,False,(),("sleep-onset",),False),
 ("How often have you woken during the night and struggled to return to sleep?",ALL_AGES,"frequency_5",2,False,False,(),("sleep-maintenance",),False),
 ("How often have you awakened earlier than you intended?",ALL_AGES,"frequency_5",1,False,False,(),("early-waking",),False),
 ("How often has sleep left you feeling unrested?",ALL_AGES,"frequency_5",2,False,False,(),("rest",),False),
 ("How severe has daytime tiredness from poor sleep been?",ALL_AGES,"severity_5",2,False,False,(),("fatigue",),False),
 ("How often have you slept much more than is usual for you?",ALL_AGES,"frequency_5",1,False,False,(),("oversleeping",),False),
 # appetite (4)
 ("How often have you had much less appetite than usual?",ALL_AGES,"frequency_5",2,False,False,(),("low-appetite",),False),
 ("How often have you eaten much more than usual when distressed?",ALL_AGES,"frequency_5",1,False,False,(),("high-appetite",),False),
 ("How severe have recent changes in your energy or physical wellbeing felt?",ALL_AGES,"severity_5",2,False,False,(),("energy",),False),
 ("How often has caring for basic physical needs, such as meals or hygiene, felt difficult?",ALL_AGES,"frequency_5",3,False,False,(),("self-care",),False),
 # anger (5)
 ("How often have you felt irritable or easily frustrated?",ALL_AGES,"frequency_5",2,False,False,(),("irritability",),False),
 ("How severe have bursts of anger felt recently?",ALL_AGES,"severity_5",2,False,False,(),("anger",),False),
 ("How often have you reacted more strongly than you intended?",ALL_AGES,"frequency_5",2,False,False,(),("reactivity",),False),
 ("How often have you felt unable to settle after becoming upset?",ALL_AGES,"frequency_5",2,False,False,(),("agitation",),False),
 ("How often have conflicts increased because you felt on edge?",ALL_AGES,"frequency_5",1,False,False,(),("conflict",),False),
 # social withdrawal (6)
 ("How often have you avoided talking with people you usually trust?",ALL_AGES,"frequency_5",2,False,False,(),("withdrawal",),False),
 ("How often have you declined activities because being with others felt difficult?",ALL_AGES,"frequency_5",2,False,False,(),("activities",),False),
 ("How often have you kept your feelings hidden even when you wanted support?",ALL_AGES,"frequency_5",2,False,False,(),("concealment",),False),
 ("How often have messages or calls from others felt too difficult to answer?",ALL_AGES,"frequency_5",1,False,False,(),("communication",),False),
 ("How severe has discomfort around groups of people felt?",ALL_AGES,"severity_5",2,False,False,(),("groups",),False),
 ("How often have you felt safer being alone even when isolation was painful?",ALL_AGES,"frequency_5",2,False,False,(),("isolation",),False),
 # hopelessness (6)
 ("How often has the future felt difficult to imagine positively?",ALL_AGES,"frequency_5",3,False,False,(),("future",),False),
 ("How often have you felt that your situation may never improve?",ALL_AGES,"frequency_5",3,False,False,(),("improvement",),False),
 ("How severe has discouragement felt when you think about the next few weeks?",ALL_AGES,"severity_5",2,False,False,(),("discouragement",),False),
 ("How often have your efforts felt pointless?",ALL_AGES,"frequency_5",3,False,False,(),("futility",),False),
 ("How often have setbacks made it hard to try again?",ALL_AGES,"frequency_5",2,False,False,(),("setbacks",),False),
 ("How often have you felt trapped with no acceptable way forward?",ALL_AGES,"frequency_5",3,False,False,(),("trapped",),False),
 # concentration (5)
 ("How often have you found it hard to concentrate on a task?",ALL_AGES,"frequency_5",2,False,False,(),("concentration",),False),
 ("How often have you lost track of conversations or instructions?",ALL_AGES,"frequency_5",1,False,False,(),("attention",),False),
 ("How often has making an ordinary decision felt difficult?",ALL_AGES,"frequency_5",2,False,False,(),("decisions",),False),
 ("How often have you forgotten routine things because your mind felt overloaded?",ALL_AGES,"frequency_5",1,False,False,(),("forgetfulness",),False),
 ("How severe has mental fog or slowed thinking felt?",ALL_AGES,"severity_5",2,False,False,(),("cognitive",),False),
 # functioning (7)
 ("How much have emotional difficulties affected your ability to manage daily responsibilities?",ALL_AGES,"severity_5",3,False,False,(),("daily-function",),True),
 ("How often has starting a necessary task felt too difficult?",ALL_AGES,"frequency_5",2,False,False,(),("task-initiation",),False),
 ("How often have you left important tasks unfinished because of distress?",ALL_AGES,"frequency_5",2,False,False,(),("completion",),False),
 ("How severe has difficulty maintaining your usual routine been?",ALL_AGES,"severity_5",2,False,False,(),("routine",),False),
 ("How often have you needed more help than usual with everyday activities?",ALL_AGES,"frequency_5",2,False,False,(),("assistance",),False),
 ("How often has distress affected your ability to attend appointments or commitments?",ALL_AGES,"frequency_5",2,False,False,(),("commitments",),False),
 ("How often have you felt unable to deal with a problem that needed attention?",ALL_AGES,"frequency_5",2,False,False,(),("problem-solving",),False),
 # safety (9): Q064-Q072
 ("Recently, have you had thoughts about harming yourself?",ALL_AGES,"safety_yes_no",4,True,False,(),("self-harm",),True),
 ("Are you in immediate danger from yourself or someone else right now?",ALL_AGES,"safety_yes_no",4,True,False,("Q064","Q069"),("immediate-danger",),False),
 ("Do you feel able to keep yourself safe right now?",ALL_AGES,"safety_yes_no",4,True,True,("Q064","Q065"),("stay-safe",),False),
 ("Have you made preparations to harm yourself?",ALL_AGES,"safety_yes_no",4,True,False,("Q064",),("preparation",),False),
 ("Is there something nearby that you might use to harm yourself?",ALL_AGES,"safety_yes_no",4,True,False,("Q064",),("access",),False),
 ("Do you currently feel unsafe because of another person's actions?",ALL_AGES,"safety_yes_no",4,True,False,(),("other-danger",),False),
 ("Do you need immediate help to stay safe?",ALL_AGES,"safety_yes_no",4,True,False,("Q064","Q065","Q066","Q069"),("urgent-help",),False),
 ("Is hopelessness so severe that staying safe feels difficult?",ALL_AGES,"safety_yes_no",4,True,False,("Q046","Q047","Q048","Q049","Q050","Q051"),("hopeless-safety",),False),
 ("Do you have a safe person or place you can reach if distress increases?",ALL_AGES,"safety_yes_no",4,True,True,("Q064","Q069"),("safety-resource",),False),
 # social support (6)
 ("Is there someone available whom you could contact for support today?",ALL_AGES,"yes_no",3,False,True,(),("available-support",),True),
 ("How often have you felt listened to by someone you trust?",ALL_AGES,"frequency_5",2,False,True,(),("listened-to",),False),
 ("How often have you been able to ask for help when you needed it?",ALL_AGES,"frequency_5",2,False,True,(),("help-seeking",),False),
 ("How severe has difficulty finding practical support been?",ALL_AGES,"severity_5",2,False,False,(),("practical-support",),False),
 ("How often have you felt supported by your community or local network?",ALL_AGES,"frequency_5",1,False,True,(),("community",),False),
 ("How confident are you that a trusted person would respond if you contacted them?",ALL_AGES,"likert_5",2,False,True,(),("support-confidence",),False),
 # family (6)
 ("How often has tension at home affected your emotional wellbeing?",ALL_AGES,"frequency_5",2,False,False,(),("home-tension",),False),
 ("How safe and respected have you felt within your family environment?",ALL_AGES,"likert_5",3,False,True,(),("family-safety",),False),
 ("How often have family expectations felt overwhelming?",ADOLESCENT+YOUNG,"frequency_5",2,False,False,(),("expectations",),False),
 ("How often have caregiving responsibilities for family members felt overwhelming?",ADULTS+OLDER,"frequency_5",2,False,False,(),("caregiving",),False),
 ("How often has it been difficult to discuss your needs with family?",ALL_AGES,"frequency_5",2,False,False,(),("communication",),False),
 ("How severe has conflict about independence or household decisions felt?",ALL_AGES,"severity_5",1,False,False,(),("independence",),False),
 # education/work (8)
 ("How often has schoolwork felt difficult because of emotional stress?",ADOLESCENT,"frequency_5",2,False,False,(),("school",),False),
 ("How often have bullying, exclusion, or hurtful peer interactions affected you?",ADOLESCENT,"frequency_5",3,False,False,(),("bullying",),False),
 ("How severe has pressure about exams or future study felt?",ADOLESCENT+YOUNG,"severity_5",2,False,False,(),("study-pressure",),False),
 ("How often have college, training, or career decisions felt overwhelming?",YOUNG,"frequency_5",2,False,False,(),("transition",),False),
 ("How often has stress at work affected you after working hours?",WORKING_AGES,"frequency_5",2,False,False,(),("work-stress",),False),
 ("How secure do you feel about your current work, study, or training situation?",WORKING_AGES,"likert_5",2,False,True,(),("security",),False),
 ("How often have responsibilities at work or home exceeded what you could manage?",ADULTS,"frequency_5",2,False,False,(),("workload",),False),
 ("How severe has adapting to retirement or reduced work responsibilities felt?",OLDER,"severity_5",2,False,False,(),("retirement",),False),
 # financial (5)
 ("How often have money concerns caused ongoing worry?",WORKING_AGES+OLDER,"frequency_5",2,False,False,(),("money-worry",),False),
 ("How severe has difficulty meeting basic expenses felt?",WORKING_AGES+OLDER,"severity_5",3,False,False,(),("basic-expenses",),False),
 ("How often have education costs or dependence on others for money caused stress?",ADOLESCENT+YOUNG,"frequency_5",2,False,False,(),("education-cost",),False),
 ("How often have financial responsibilities toward family felt overwhelming?",ADULTS,"frequency_5",2,False,False,(),("family-finance",),False),
 ("How confident are you that you can access help for an urgent financial need?",ALL_AGES,"likert_5",1,False,True,(),("financial-support",),False),
 # relationship (6)
 ("How often has conflict in an important relationship affected your wellbeing?",ALL_AGES,"frequency_5",2,False,False,(),("conflict",),False),
 ("How respected have you felt in your close relationships?",ALL_AGES,"likert_5",2,False,True,(),("respect",),False),
 ("How often have you worried about rejection or losing an important relationship?",ADOLESCENT+YOUNG,"frequency_5",2,False,False,(),("rejection",),False),
 ("How severe has strain between family, work, and relationship responsibilities felt?",ADULTS,"severity_5",2,False,False,(),("role-strain",),False),
 ("How often have you felt controlled or unable to express your choices in a relationship?",ALL_AGES,"frequency_5",3,False,False,(),("control",),False),
 ("How often have changes in companionship or partnership caused distress?",OLDER,"frequency_5",2,False,False,(),("companionship",),False),
 # physical symptoms (5)
 ("How often has stress been accompanied by headaches or body pain?",ALL_AGES,"frequency_5",1,False,False,(),("pain",),False),
 ("How often has your heart raced or breathing changed when distressed?",ALL_AGES,"frequency_5",2,False,False,(),("arousal",),False),
 ("How often have stomach discomfort or nausea appeared during stress?",ALL_AGES,"frequency_5",1,False,False,(),("stomach",),False),
 ("How severe has muscle tension or restlessness felt?",ALL_AGES,"severity_5",2,False,False,(),("tension",),False),
 ("How often have physical health concerns increased emotional distress?",OLDER,"frequency_5",2,False,False,(),("health",),False),
 # avoidance (5)
 ("How often have you avoided places that remind you of a difficult experience?",ALL_AGES,"frequency_5",2,False,False,(),("places",),False),
 ("How often have you avoided thoughts or conversations about what happened?",ALL_AGES,"frequency_5",2,False,False,(),("thoughts",),False),
 ("How often have you changed routines mainly to avoid reminders?",ALL_AGES,"frequency_5",2,False,False,(),("routine",),False),
 ("How severe has fear of leaving a familiar or safe place felt?",ALL_AGES,"severity_5",2,False,False,(),("leaving",),False),
 ("How often has avoidance prevented you from doing something important?",ALL_AGES,"frequency_5",3,False,False,(),("function",),False),
 # hypervigilance (5)
 ("How often have you felt constantly watchful for possible danger?",ALL_AGES,"frequency_5",3,False,False,(),("watchful",),False),
 ("How often have sudden sounds or movements startled you strongly?",ALL_AGES,"frequency_5",2,False,False,(),("startle",),False),
 ("How often have you checked doors, surroundings, or people repeatedly for safety?",ALL_AGES,"frequency_5",2,False,False,(),("checking",),False),
 ("How severe has difficulty relaxing in a safe setting felt?",ALL_AGES,"severity_5",2,False,False,(),("relaxing",),False),
 ("How often have you had trouble focusing because you were monitoring possible threats?",ALL_AGES,"frequency_5",2,False,False,(),("threat-monitoring",),False),
 # substance use (4)
 ("How often have you used alcohol or another substance mainly to cope with difficult feelings?",WORKING_AGES+OLDER,"frequency_5",2,False,False,(),("coping-use",),False),
 ("How often has substance use caused difficulty with responsibilities or relationships?",WORKING_AGES+OLDER,"frequency_5",3,False,False,(),("impact",),False),
 ("How difficult has it felt to reduce a substance you wanted to use less?",WORKING_AGES+OLDER,"severity_5",2,False,False,(),("control",),False),
 ("How often have you felt pressured by peers to use alcohol, tobacco, or another substance?",ADOLESCENT+YOUNG,"frequency_5",2,False,False,(),("peer-pressure",),False),
 # loneliness (5)
 ("How often have you felt alone even when other people were nearby?",ALL_AGES,"frequency_5",2,False,False,(),("loneliness",),False),
 ("How often have you felt that nobody understands what you are going through?",ALL_AGES,"frequency_5",2,False,False,(),("understood",),False),
 ("How severe has lack of companionship felt?",ALL_AGES,"severity_5",2,False,False,(),("companionship",),False),
 ("How often have school or peer changes left you feeling isolated?",ADOLESCENT+YOUNG,"frequency_5",2,False,False,(),("peer-isolation",),False),
 ("How often have health, mobility, or living changes limited contact with others?",OLDER,"frequency_5",2,False,False,(),("mobility-isolation",),False),
 # grief (5)
 ("How often have thoughts of a person, place, role, or life you lost caused distress?",ALL_AGES,"frequency_5",2,False,False,(),("loss",),False),
 ("How severe has grief felt during the past two weeks?",ALL_AGES,"severity_5",2,False,False,(),("grief",),False),
 ("How often have reminders of a loss disrupted your day?",ALL_AGES,"frequency_5",2,False,False,(),("reminders",),False),
 ("How often have you felt unable to talk with anyone about a loss?",ALL_AGES,"frequency_5",2,False,False,(),("grief-support",),False),
 ("How often have several losses or major changes felt too much to process?",OLDER,"frequency_5",3,False,False,(),("cumulative-loss",),False),
 # control (5)
 ("How often have important parts of your life felt outside your control?",ALL_AGES,"frequency_5",2,False,False,(),("control",),False),
 ("How much choice do you feel you have in decisions that affect you?",ALL_AGES,"likert_5",2,False,True,(),("choice",),False),
 ("How confident are you that you can influence at least one current problem?",ALL_AGES,"likert_5",2,False,True,(),("agency",),False),
 ("How often have rules or decisions made by others left you feeling powerless?",ADOLESCENT+OLDER,"frequency_5",2,False,False,(),("dependence",),False),
 ("How severe has uncertainty about your next steps felt?",ALL_AGES,"severity_5",2,False,False,(),("uncertainty",),False),
 # coping (6)
 ("How confident are you that you can calm yourself when distress begins?",ALL_AGES,"likert_5",2,False,True,(),("self-soothing",),False),
 ("How often have your usual coping methods helped even a little?",ALL_AGES,"frequency_5",2,False,True,(),("coping",),False),
 ("How often have you been able to take one manageable step when overwhelmed?",ALL_AGES,"frequency_5",2,False,True,(),("small-step",),False),
 ("How severe has difficulty recovering after a stressful event felt?",ALL_AGES,"severity_5",2,False,False,(),("recovery",),False),
 ("How often have you used a healthy activity to release tension?",ALL_AGES,"frequency_5",1,False,True,(),("healthy-activity",),False),
 ("How confident are you that you know what to do if distress becomes stronger?",ALL_AGES,"likert_5",2,False,True,(),("plan",),False),
 # protective factors (7)
 ("How connected do you currently feel to at least one person or community?",ALL_AGES,"likert_5",2,False,True,(),("connection",),False),
 ("How often have you noticed a reason to continue with your plans for the future?",ALL_AGES,"frequency_5",3,False,True,(),("future-reason",),False),
 ("How confident are you that professional or community support is available if needed?",ALL_AGES,"likert_5",2,False,True,(),("service-access",),False),
 ("How often has a routine, responsibility, belief, or relationship helped you keep going?",ALL_AGES,"frequency_5",2,False,True,(),("meaning",),False),
 ("How safe does your usual living environment feel today?",ALL_AGES,"likert_5",3,False,True,(),("environment-safety",),False),
 ("How confident are you that you can name one person, place, or service to contact in a crisis?",ALL_AGES,"likert_5",3,False,True,(),("crisis-contact",),False),
 ("How often have you felt hopeful about even one small part of the near future?",ALL_AGES,"frequency_5",2,False,True,(),("hope",),False),
]

DOMAIN_COUNTS = (
    ("mood", 8), ("anxiety", 8), ("trauma", 8), ("sleep", 6),
    ("physical_wellbeing", 4), ("anger", 5), ("social_withdrawal", 6),
    ("hopelessness", 6), ("concentration", 5), ("functioning", 7),
    ("safety", 9), ("social_support", 6), ("family", 6),
    ("education_work", 8), ("financial", 5), ("relationship", 6),
    ("physical_stress", 5), ("avoidance", 5), ("hypervigilance", 5),
    ("substance_use", 4), ("loneliness", 5), ("grief", 5),
    ("sense_of_control", 5), ("coping", 6), ("protective_factors", 7),
)
_domains = tuple(domain for domain, count in DOMAIN_COUNTS for _ in range(count))
if len(_domains) != len(SPECS):
    raise ValueError("Question bank domain counts do not match question specs")
QUESTIONS = tuple(Question(f"Q{index:03d}", spec[0], domain, *spec[1:])
                  for index, (domain, spec) in enumerate(zip(_domains, SPECS), 1))
BY_ID = {question.id: question for question in QUESTIONS}
CORE_IDS = tuple(question.id for question in QUESTIONS if question.core)
SAFETY_IDS = tuple(question.id for question in QUESTIONS if question.domain == "safety")

RESPONSE_OPTIONS = {
    "frequency_5": ("Never", "Rarely", "Sometimes", "Often", "Almost always"),
    "severity_5": ("None", "Mild", "Moderate", "Severe", "Very severe"),
    "yes_no": ("No", "Yes"),
    "safety_yes_no": ("No", "Yes"),
    "likert_5": ("Not at all", "A little", "Somewhat", "Mostly", "Completely"),
}


def validate_bank():
    errors = []
    if len(QUESTIONS) != len(BY_ID): errors.append("Question IDs must be unique")
    for question in QUESTIONS:
        if question.response_type not in RESPONSE_OPTIONS: errors.append(f"{question.id}: response type")
        if not 1 <= question.severity_weight <= 4: errors.append(f"{question.id}: weight")
        if not question.age_groups or not set(question.age_groups) <= set(ALL_AGES): errors.append(f"{question.id}: ages")
        for parent in question.follow_up_for:
            if parent not in BY_ID: errors.append(f"{question.id}: missing parent {parent}")
    if not set(SAFETY_IDS) <= {q.id for q in QUESTIONS if set(q.age_groups) == set(ALL_AGES)}:
        errors.append("Every safety question must be universal")
    if errors: raise ValueError("; ".join(errors))
    return True


validate_bank()
