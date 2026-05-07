"""Hand-written mock fixtures for the demo site, used until real inference
data lands (issue #13).

The 10 scoped opinions form a coherent qualified-immunity / §1983 cluster
(SCOTUS Pearson/Saucier/Harlow + lower-court applications). Real cluster IDs
and real opinion paragraphs (extracted from CourtListener) are used for 9 of
the 10; the 10th is a fabricated D. Utah district-court opinion to demonstrate
Path-B (heavily-cited) scope.

Data shape mirrors the production citator schema documented in
ai-research/citator_launch_plan/db_design.md. Each treatment relationship is
authored once on the citing side; build_data.py derives the cited side's
view (no double-authoring, no drift). External (non-scoped) citing-case
metadata lives in EXTERNAL_OPINIONS so build_data.py can populate cited_by
views for those edges too.
"""

from __future__ import annotations

# ── Scoped-in cluster IDs ──────────────────────────────────────────────
SCOPED_CLUSTER_IDS = frozenset(
    {
        145918,  # Pearson v. Callahan (SCOTUS 2009)
        118449,  # Saucier v. Katz (SCOTUS 2001)
        110763,  # Harlow v. Fitzgerald (SCOTUS 1982)
        1425860,  # Callahan v. Millard County (10th Cir. 2007)
        220962,  # Henry v. Purnell (4th Cir. 2011 en banc)
        203857,  # Maldonado v. Fontanes (1st Cir. 2009)
        807646,  # Lacey v. Arpaio (9th Cir. 2012 en banc)
        2219834,  # Martinez v. City of Schenectady (NY Ct App 2001)
        1801687,  # Hernandez v. City of Pomona (Cal. 2009)
        9999001,  # Callahan v. Millard County Sheriff (D. Utah, fabricated)
    }
)

# ── Court display names ────────────────────────────────────────────────
COURT_DISPLAY = {
    "scotus": "U.S. Supreme Court",
    "ca1": "First Circuit",
    "ca2": "Second Circuit",
    "ca4": "Fourth Circuit",
    "ca9": "Ninth Circuit",
    "ca10": "Tenth Circuit",
    "utd": "U.S. District Court (D. Utah)",
    "ny": "New York Court of Appeals",
    "cal": "California Supreme Court",
    "dist": "U.S. District Court",
}

# ── Court hierarchy levels ─────────────────────────────────────────────
# Lower number = higher court. Used to validate that predicted
# (treatment, citing_court, cited_court) tuples are hierarchically
# possible. Production gap: not stored on `Court` upstream; tracked in
# db_design.md § Production data gaps.
COURT_LEVEL = {
    "scotus": 0,
    "ca1": 1,
    "ca2": 1,
    "ca3": 1,
    "ca4": 1,
    "ca5": 1,
    "ca6": 1,
    "ca7": 1,
    "ca8": 1,
    "ca9": 1,
    "ca10": 1,
    "ca11": 1,
    "cadc": 1,
    "cafc": 1,
    "ny": 1,  # state court of last resort, treated at circuit-equivalent
    "cal": 1,
    "utd": 2,
    "dist": 2,
}

# Courts whose decisions are not subject to direct appellate review.
# SCOTUS is final on federal-law questions; state courts of last resort
# are final on state-law questions (SCOTUS can review them on federal
# questions, but for the demo we treat them as last-resort).
COURTS_OF_LAST_RESORT = frozenset({"scotus", "ny", "cal"})

# Higher-level grouping for the search-results court filter rail. Each
# court key maps to a category whose top-level checkbox lets users select
# every court in the group at once (e.g., all circuit courts).
COURT_CATEGORY = {
    "scotus": "scotus",
    "ca1": "circuit",
    "ca2": "circuit",
    "ca3": "circuit",
    "ca4": "circuit",
    "ca5": "circuit",
    "ca6": "circuit",
    "ca7": "circuit",
    "ca8": "circuit",
    "ca9": "circuit",
    "ca10": "circuit",
    "ca11": "circuit",
    "cadc": "circuit",
    "cafc": "circuit",
    "ny": "state_supreme",
    "cal": "state_supreme",
    "utd": "district",
    "dist": "district",
}

CATEGORY_DISPLAY = {
    "scotus": "U.S. Supreme Court",
    "circuit": "U.S. Circuit courts",
    "state_supreme": "State COLR",
    "district": "U.S. District courts",
}

CATEGORY_ORDER = ("scotus", "circuit", "district", "state_supreme")

# Jurisdiction split for the search-results filter rail. Each category
# belongs to exactly one jurisdiction, and the filter rail's top-level
# parent checkbox toggles every court within that jurisdiction.
CATEGORY_JURISDICTION = {
    "scotus": "federal",
    "circuit": "federal",
    "district": "federal",
    "state_supreme": "state",
}

JURISDICTION_DISPLAY = {
    "federal": "Federal",
    "state": "State",
}

JURISDICTION_ORDER = ("federal", "state")


# ── Helpers ────────────────────────────────────────────────────────────
def opinion(
    cluster_id: int,
    case_name: str,
    docket_number: str,
    citations: list[str],
    court: str,
    date_filed: str,
    document_text: str,
) -> dict:
    """A scoped-in opinion: rendered as its own page on the demo site."""
    return {
        "cluster_id": cluster_id,
        "case_name": case_name,
        "docket_number": docket_number,
        "citations": citations,
        "court": court,
        "date_filed": date_filed,
        "document_text": document_text,
    }


def external_op(
    cluster_id: int,
    case_name: str,
    docket_number: str,
    citations: list[str],
    court: str,
    date_filed: str,
) -> dict:
    """Stand-in metadata for a citing or cited case that isn't in the
    scoped 10. Used to populate authorities[] / cited_by[] entries for
    edges that touch non-scoped clusters. Doesn't get its own opinion
    page in the demo.
    """
    return {
        "cluster_id": cluster_id,
        "case_name": case_name,
        "docket_number": docket_number,
        "citations": citations,
        "court": court,
        "date_filed": date_filed,
    }


def edge(
    citing_cluster_id: int,
    cited_cluster_id: int,
    treatment: str,
    quote: str,
    rationale: str,
    section_context: str = "",
    source: str = "model",
    expert_treatment: str | None = None,
    **_legacy: object,
) -> dict:
    """A single treatment relationship — the canonical row.

    - `source` mirrors production's CitatorTreatment.source (model /
      expert / user_correction). The demo's display indicator (🔵 / ⚪ /
      🟠) is computed from source + expert_treatment at render time.
    - `expert_treatment` is a demo-only field: when present and different
      from `treatment` on a model row, the row is flagged 🟠 (model
      disagrees with expert). Production derives this from joining a
      paired-expert row.
    - `section_context` is a paragraph from the citing opinion containing
      the quote — used to slice real before/after sentences in the
      Cited By tab. Production analog: CitatorExtractedCitation.section_context.
    - `**_legacy` swallows obsolete keyword arguments (e.g., `section_id`)
      so existing entries can be cleaned up incrementally.
    """
    return {
        "citing_cluster_id": citing_cluster_id,
        "cited_cluster_id": cited_cluster_id,
        "treatment": treatment,
        "quote": quote,
        "rationale": rationale,
        "section_context": section_context,
        "source": source,
        "expert_treatment": expert_treatment,
    }


# ── 10 scoped opinions (real paragraphs from CourtListener) ────────────

PEARSON_BODY = """## I

This is an action brought by respondent under Rev. Stat. §1979, 42 U. S. C. §1983, against state law enforcement officers who conducted a warrantless search of his house incident to his arrest for the sale of methamphetamine to an undercover informant whom he had voluntarily admitted to the premises. The Court of Appeals held that petitioners were not entitled to summary judgment on qualified immunity grounds. Following the procedure we mandated in <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U. S. 194 (2001), the Court of Appeals held, first, that respondent adduced facts sufficient to make out a violation of the Fourth Amendment and, second, that the unconstitutionality of the officers' conduct was clearly established.

We now hold that the <citedCase data-cluster-id="118449">Saucier</citedCase> procedure should not be regarded as an inflexible requirement and that petitioners are entitled to qualified immunity on the ground that it was not clearly established at the time of the search that their conduct was unconstitutional. We therefore reverse.

## II

The doctrine of qualified immunity protects government officials "from liability for civil damages insofar as their conduct does not violate clearly established statutory or constitutional rights of which a reasonable person would have known." <citedCase data-cluster-id="110763">Harlow v. Fitzgerald</citedCase>, 457 U. S. 800, 818 (1982). Qualified immunity balances two important interests — the need to hold public officials accountable when they exercise power irresponsibly and the need to shield officials from harassment, distraction, and liability when they perform their duties reasonably.

## III

On appeal, a divided panel of the Tenth Circuit held that petitioners' conduct violated respondent's Fourth Amendment rights. <citedCase data-cluster-id="1425860">Callahan v. Millard Cty.</citedCase>, 494 F. 3d 891, 895–899 (2007). For the reasons set forth above, we reverse and remand for further proceedings consistent with this opinion."""


SAUCIER_BODY = """## I

In this case a citizen alleged excessive force was used to arrest him. The arresting officer asserted the defense of qualified immunity. The matter we address is whether the requisite analysis to determine qualified immunity is so intertwined with the question whether the officer used excessive force in making the arrest that qualified immunity and constitutional violation issues should be treated as one question, to be decided by the trier of fact. The Court of Appeals held the inquiries do merge into a single question. We now reverse and hold that the ruling on qualified immunity requires an analysis not susceptible of fusion with the question whether unreasonable force was used in making the arrest.

## II

A court required to rule upon the qualified immunity issue must consider, then, this threshold question: Taken in the light most favorable to the party asserting the injury, do the facts alleged show the officer's conduct violated a constitutional right? This must be the initial inquiry. If no constitutional right would have been violated were the allegations established, there is no necessity for further inquiries concerning qualified immunity. On the other hand, if a violation could be made out on a favorable view of the parties' submissions, the next, sequential step is to ask whether the right was clearly established.

## III

The approach the Court of Appeals adopted — to deny summary judgment any time a material issue of fact remains on the excessive force claim — could undermine the goal of qualified immunity to "avoid excessive disruption of government and permit the resolution of many insubstantial claims on summary judgment." <citedCase data-cluster-id="110763">Harlow v. Fitzgerald</citedCase>, 457 U. S. 800, 818 (1982). If the law did not put the officer on notice that his conduct would be clearly unlawful, summary judgment based on qualified immunity is appropriate."""


HARLOW_BODY = """## I

The issue in this case is the scope of the immunity available to the senior aides and advisers of the President of the United States in a suit for damages based upon their official acts.

In this suit for civil damages petitioners Bryce Harlow and Alexander Butterfield are alleged to have participated in a conspiracy to violate the constitutional and statutory rights of the respondent A. Ernest Fitzgerald. Respondent avers that petitioners entered the conspiracy in their capacities as senior White House aides to former President Richard M. Nixon.

## II

We therefore hold that government officials performing discretionary functions, generally are shielded from liability for civil damages insofar as their conduct does not violate clearly established statutory or constitutional rights of which a reasonable person would have known.

By defining the limits of qualified immunity essentially in objective terms, we provide no license to lawless conduct. The public interest in deterrence of unlawful conduct and in compensation of victims remains protected by a test that focuses on the objective legal reasonableness of an official's acts.

## III

Reliance on the objective reasonableness of an official's conduct, as measured by reference to clearly established law, should avoid excessive disruption of government and permit the resolution of many insubstantial claims on summary judgment. On summary judgment, the judge appropriately may determine, not only the currently applicable law, but whether that law was clearly established at the time an action occurred. If the law at that time was not clearly established, an official could not reasonably be expected to anticipate subsequent legal developments, nor could he fairly be said to "know" that the law forbade conduct not previously identified as unlawful."""


CALLAHAN_10TH_BODY = """## Background

In this civil rights action, Plaintiff-Appellant Afton Callahan appeals from the district court's grant of summary judgment in favor of the numerous Defendant-Appellees. The district court held that the individual officers were entitled to qualified immunity because Mr. Callahan did not establish that the officers violated a clearly established right. Holding that the district court was correct in its determination that Mr. Callahan's constitutional rights were violated, but incorrect in its determination that these rights were not clearly established, we reverse in part and remand.

This appeal evolves from a police raid of Mr. Callahan's home on March 19, 2002. Earlier in the day, a confidential informant — who assisted the Central Utah Narcotics Task Force after being charged with possession of methamphetamine — saw Mr. Callahan and discussed a potential sale of methamphetamine later that day. The confidential informant then informed an officer of the task force of the conversation.

## Discussion

Once a qualified immunity defense is asserted, the burden shifts to the plaintiff. First, the plaintiff must "establish that the defendant violated a constitutional right." If the plaintiff fails to satisfy this initial requirement, the court's inquiry ends. If no constitutional right would have been violated were the allegations established, there is no necessity for further inquiries concerning qualified immunity — quoting <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U.S. 194, 201 (2001). If the plaintiff establishes that a constitutional right was violated, then the plaintiff must also show that the violated right was clearly established.

Here, the officers knew they had no warrant; Mr. Callahan had not consented to their entry; and his consent to the entry of an informant could not reasonably be interpreted to extend to them. They do not argue on appeal that exigent circumstances justified their entry. The officers are not protected by qualified immunity. AFFIRMED IN PART, REVERSED IN PART, AND REMANDED."""


HENRY_BODY = """## I

Without warning, Officer Robert Purnell shot Frederick Henry, an unarmed man wanted for misdemeanor failure to pay child support, when he started running away. In the ensuing §1983 action, the parties stipulated that Purnell had intended to use his Taser rather than his gun and the district court granted him summary judgment. However, because Tennessee v. Garner prohibits shooting suspects who pose no significant threat of death or serious physical threat, and because Purnell's use of force could be viewed by a jury as objectively unreasonable, we reverse and remand.

Since this case stems from the grant of summary judgment for Purnell, we recount the facts in the light most favorable to the non-movant, Henry. In 2003, a Maryland state court ordered Henry to either pay child support or report to jail on September 8, 2003. When Henry did not comply, a warrant was issued for his arrest on October 9, 2003 for second degree escape.

## II

Qualified immunity protects officers who commit constitutional violations but who, in light of clearly established law, could reasonably believe that their actions were lawful. <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U.S. 194, 206 (2001), overruled in part, <citedCase data-cluster-id="145918">Pearson v. Callahan</citedCase>, 129 S. Ct. 808 (2009). Following the Supreme Court's recent decision in Pearson, we exercise our discretion to use the two-step procedure of Saucier, that asks first whether a constitutional violation occurred and second whether the right violated was clearly established.

## III

The second prong is "a test that focuses on the objective legal reasonableness of an official's acts." <citedCase data-cluster-id="110763">Harlow v. Fitzgerald</citedCase>, 457 U.S. 800, 819 (1982). An official will not be held liable unless the contours of the right he is alleged to have violated were sufficiently clear that a reasonable official would understand that what he is doing violates that right. Purnell's use of deadly force against Henry was objectively unreasonable and violated clearly established law."""


MALDONADO_BODY = """## I

Residents of three public housing complexes brought a civil rights suit under 42 U.S.C. §1983 against the Mayor of Barceloneta, Puerto Rico, protesting the precipitous seizures and cruel killings of their pet cats and dogs. The twenty named plaintiff families assert violations of their Fourth Amendment rights to be free from unreasonable seizures of their "effects" and their Fourteenth Amendment procedural and substantive due process rights.

The Mayor, in his personal capacity, moved to dismiss all damages claims against him on grounds of qualified immunity. That motion was denied; the Mayor has taken an interlocutory appeal. We are informed that discovery is being completed and that the case is nearly ready for trial.

## II

In <citedCase data-cluster-id="145918">Pearson v. Callahan</citedCase>, 129 S. Ct. 808 (2009), the Court reiterated that the qualified immunity inquiry is a two-part test. <citedCase data-cluster-id="145918">Pearson</citedCase> also held that while it is frequently appropriate for courts to answer each step in turn, it is not mandatory that courts follow the two-step analysis sequentially. Courts have discretion to decide whether, on the facts of a particular case, it is worthwhile to address first whether the facts alleged make out a violation of a constitutional right.

## III

The relevant, dispositive inquiry in determining whether a right is clearly established is whether it would be clear to a reasonable officer that his conduct was unlawful in the situation he confronted — quoting <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U.S. at 202. That is, the salient question is whether the state of the law at the time of the alleged violation gave the defendant fair warning that his particular conduct was unconstitutional. We affirm the denial of the Mayor's motion for qualified immunity on the Fourth Amendment and Fourteenth Amendment procedural due process claims."""


LACEY_BODY = """## I

This §1983 case concerns allegations of unlawful conduct by officials in the Maricopa County Sheriff's Office and the Maricopa County Attorney's Office, conduct which culminated in the late-night arrests of Michael Lacey and Jim Larkin, owners of the Phoenix New Times. The district court dismissed all federal claims, and remanded all state law claims back to the Arizona courts. We affirm in part and reverse in part, finding that Lacey adequately alleged several causes of action for which the defendants are not entitled to immunity.

## II

Determining whether a defendant is entitled to qualified immunity involves a two-pronged analysis. First, we ask whether the facts alleged show the officer's conduct violated a constitutional right — <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U.S. 194, 201 (2001), overruled in part by <citedCase data-cluster-id="145918">Pearson</citedCase>, 555 U.S. at 235–236. Second, we must ask whether the right was clearly established. We have the discretion to decide which of the two prongs of the qualified immunity analysis should be addressed first in light of the circumstances in the particular case at hand.

## III

Qualified immunity "represents the norm" for government officials exercising discretionary authority, <citedCase data-cluster-id="110763">Harlow v. Fitzgerald</citedCase>, 457 U.S. 800, 807 (1982), including prosecutors who are not acting as an advocate for the state and may not be entitled to absolute immunity. We have little difficulty concluding that Arpaio is not entitled to qualified immunity on Lacey's First Amendment retaliation claims. Lacey may proceed on those claims.

The First Circuit's analysis in <citedCase data-cluster-id="203857">Maldonado v. Fontanes</citedCase> addressed substantive due process claims with no allegation of First Amendment retaliation. Here, Lacey's claims are anchored in retaliation for newsgathering, a context Maldonado did not consider."""


MARTINEZ_BODY = """## I

The long history of this appeal began in September 1987 when, pursuant to a search warrant, defendants — Schenectady police officers — entered the residence of plaintiff Melody Martinez, seized four ounces of cocaine from a dresser drawer in her bedroom and arrested her.

Plaintiff then brought suit in the United States District Court for the Northern District of New York against the City of Schenectady and five officers involved in the relevant events, asserting a claim for damages under 42 USC §1983, common-law claims of malicious prosecution and false imprisonment, and a claim against the City for negligent hiring, training and supervision of the officers.

## II

On appeals by plaintiff and the officers, the United States Court of Appeals for the Second Circuit reversed the denial of defendants' summary judgment motion, concluding as a matter of law that qualified immunity barred the assertion of the section 1983 claims against the police officers. Applying the "corrected affidavits" doctrine previously espoused by the Second Circuit, the court reviewed all the evidence known to the officers at the time they sought the warrant to determine if under the totality of the circumstances a reasonable officer would believe that there was probable cause for the search.

## III

The present action followed in State Supreme Court against the City of Schenectady and the officers individually, asserting three causes of action: false imprisonment, malicious prosecution, and violation of article I, §§1, 11 and 12 of the New York State Constitution. We agree with Supreme Court and the Appellate Division that the "narrow remedy" established in <citedCase data-cluster-id="9920001">Brown v. State of New York</citedCase> cannot be stretched to fit the facts before us. We affirm dismissal of the complaint."""


HERNANDEZ_POMONA_BODY = """## I

We granted review in this case to consider the following question: When a federal court enters judgment in favor of the defendants on a civil rights claim brought under 42 United States Code section 1983, in which the plaintiffs seek damages for police use of deadly and constitutionally excessive force in pursuing a suspect, and the court then dismisses a supplemental state law wrongful death claim arising out of the same incident, what, if any, preclusive effect does the judgment have in a subsequent state court wrongful death action?

Before dawn on January 16, 2001, City of Pomona Police Officer Dennis Cooper was patrolling a neighborhood in a marked black-and-white police vehicle when he saw a gray Ford Thunderbird approach from the other direction with its headlights unilluminated. The Thunderbird abruptly pulled over to the curb and stopped with its engine running.

## II

At the time of the federal trial, high court precedent required the trial court first to decide whether Sanchez had violated Hernandez's constitutional rights, and then to decide the immunity question — <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase> (2001) 533 U.S. 194, 201. The high court recently changed this rule, holding that trial courts may decide the immunity question before (or without) determining whether there was a constitutional violation — <citedCase data-cluster-id="145918">Pearson v. Callahan</citedCase> (2009) 555 U.S. ___.

## III

Sanchez then moved for judgment as a matter of law, based on qualified immunity. The court granted the motion, finding that because Sanchez's "use of deadly force was reasonable under the circumstances," he "did not violate Hernandez's Fourth Amendment rights." In <citedCase data-cluster-id="2219834">Martinez v. City of Schenectady</citedCase>, the New York Court of Appeals confronted a similar preclusion question and declined to extend the state constitutional tort remedy where federal courts had already resolved the underlying §1983 claim on qualified-immunity grounds. We hold that the trial court did not err in entering judgment for defendants. We therefore reverse the Court of Appeal's judgment and remand the matter with directions to reinstate the trial court's judgment."""


D_UTAH_CALLAHAN_BODY = """## I

This is a civil-rights action brought under 42 U.S.C. §1983 by plaintiff Afton Callahan against officers of the Central Utah Narcotics Task Force, who entered his residence on March 19, 2002 incident to a controlled drug buy by a confidential informant. Plaintiff alleges that the officers' warrantless entry, predicated on the "consent-once-removed" doctrine, violated his Fourth Amendment rights.

## II

Defendants move for summary judgment on the basis of qualified immunity. The applicable framework is the two-step inquiry set out by the Supreme Court in <citedCase data-cluster-id="118449">Saucier v. Katz</citedCase>, 533 U.S. 194 (2001), governed in this Circuit by the gloss our Court of Appeals applied in earlier cases. Under that framework the Court must first ask whether the facts alleged make out a constitutional violation; only if so does the Court reach the "clearly established" prong.

## III

For the reasons set forth in our analysis above, the Court concludes that defendants' warrantless entry, when measured against the contours of the consent-once-removed doctrine as applied in this Circuit, did not violate clearly established law of which a reasonable officer would have been aware. Defendants' motion for summary judgment is GRANTED. The case is dismissed."""


# ── Scoped opinions ────────────────────────────────────────────────────
SCOPED_OPINIONS = [
    opinion(
        cluster_id=145918,
        case_name="Pearson v. Callahan",
        docket_number="07-751",
        citations=["555 U.S. 223", "129 S. Ct. 808", "172 L. Ed. 2d 565"],
        court="scotus",
        date_filed="2009-01-21",
        document_text=PEARSON_BODY,
    ),
    opinion(
        cluster_id=118449,
        case_name="Saucier v. Katz",
        docket_number="99-1977",
        citations=["533 U.S. 194", "121 S. Ct. 2151", "150 L. Ed. 2d 272"],
        court="scotus",
        date_filed="2001-06-18",
        document_text=SAUCIER_BODY,
    ),
    opinion(
        cluster_id=110763,
        case_name="Harlow v. Fitzgerald",
        docket_number="80-945",
        citations=["457 U.S. 800", "102 S. Ct. 2727", "73 L. Ed. 2d 396"],
        court="scotus",
        date_filed="1982-06-24",
        document_text=HARLOW_BODY,
    ),
    opinion(
        cluster_id=1425860,
        case_name="Callahan v. Millard County",
        docket_number="06-4135",
        citations=["494 F.3d 891"],
        court="ca10",
        date_filed="2007-07-16",
        document_text=CALLAHAN_10TH_BODY,
    ),
    opinion(
        cluster_id=220962,
        case_name="Henry v. Purnell",
        docket_number="08-7433",
        citations=["652 F.3d 524"],
        court="ca4",
        date_filed="2011-07-14",
        document_text=HENRY_BODY,
    ),
    opinion(
        cluster_id=203857,
        case_name="Maldonado v. Fontanes",
        docket_number="08-2211",
        citations=["568 F.3d 263"],
        court="ca1",
        date_filed="2009-06-04",
        document_text=MALDONADO_BODY,
    ),
    opinion(
        cluster_id=807646,
        case_name="Lacey v. Arpaio",
        docket_number="09-15703",
        citations=["693 F.3d 896"],
        court="ca9",
        date_filed="2012-08-29",
        document_text=LACEY_BODY,
    ),
    opinion(
        cluster_id=2219834,
        case_name="Martinez v. City of Schenectady",
        docket_number="N/A",
        citations=["97 N.Y.2d 78", "761 N.E.2d 560", "735 N.Y.S.2d 868"],
        court="ny",
        date_filed="2001-11-19",
        document_text=MARTINEZ_BODY,
    ),
    opinion(
        cluster_id=1801687,
        case_name="Hernandez v. City of Pomona",
        docket_number="S149499",
        citations=["46 Cal. 4th 501", "207 P.3d 506", "94 Cal. Rptr. 3d 1"],
        court="cal",
        date_filed="2009-05-28",
        document_text=HERNANDEZ_POMONA_BODY,
    ),
    opinion(
        cluster_id=9999001,
        case_name="Callahan v. Millard County Sheriff",
        docket_number="2:05-cv-00170",
        citations=["No. 2:05-cv-00170 (D. Utah 2005)"],
        court="utd",
        date_filed="2005-09-14",
        document_text=D_UTAH_CALLAHAN_BODY,
    ),
]


# ── External (non-scoped) opinions ─────────────────────────────────────
# Stand-in records for citing or cited cases that aren't in the demo's 10.
# Referenced by EDGES; surfaced in cited_by[] / authorities[] views.
EXTERNAL_OPINIONS = {
    # Fabricated non-scoped SCOTUS that affirmed Henry v. Purnell
    9999002: external_op(
        9999002,
        "Purnell v. Henry",
        "12-345",
        ["568 U.S. 901"],
        "scotus",
        "2012-10-15",
    ),
    # Citing references to Pearson (post-2009 cases)
    9100201: external_op(
        9100201,
        "Reichle v. Howards",
        "11-262",
        ["566 U.S. 658"],
        "scotus",
        "2012-06-04",
    ),
    9100202: external_op(
        9100202,
        "Plumhoff v. Rickard",
        "12-1117",
        ["572 U.S. 765"],
        "scotus",
        "2014-05-27",
    ),
    9100203: external_op(
        9100203,
        "Mullenix v. Luna",
        "14-1143",
        ["577 U.S. 7"],
        "scotus",
        "2015-11-09",
    ),
    9100204: external_op(
        9100204,
        "Hernandez v. Mesa",
        "17-1678",
        ["589 U.S. ___"],
        "scotus",
        "2020-02-25",
    ),
    # Citing references to Saucier
    9100205: external_op(
        9100205,
        "Brosseau v. Haugen",
        "03-1261",
        ["543 U.S. 194"],
        "scotus",
        "2004-12-13",
    ),
    9100206: external_op(
        9100206,
        "Scott v. Harris",
        "05-1631",
        ["550 U.S. 372"],
        "scotus",
        "2007-04-30",
    ),
    # Citing references to Harlow
    9100207: external_op(
        9100207,
        "Anderson v. Creighton",
        "85-1520",
        ["483 U.S. 635"],
        "scotus",
        "1987-06-25",
    ),
    9100208: external_op(
        9100208,
        "Wilson v. Layne",
        "98-83",
        ["526 U.S. 603"],
        "scotus",
        "1999-05-24",
    ),
    # District court below Henry (Maryland district)
    9100210: external_op(
        9100210,
        "Henry v. Purnell (D. Md.)",
        "04-cv-00342",
        ["No. JKB-04-342 (D. Md. 2008)"],
        "dist",
        "2008-09-23",
    ),
    # District court below Maldonado (D.P.R.)
    9100211: external_op(
        9100211,
        "Maldonado v. Fontanes (D.P.R.)",
        "07-cv-01711",
        ["No. 07-1711 (D.P.R. 2008)"],
        "dist",
        "2008-11-12",
    ),
    # District court below Lacey (D. Ariz.)
    9100212: external_op(
        9100212,
        "Lacey v. Arpaio (D. Ariz.)",
        "08-cv-01457",
        ["No. CV-08-1457 (D. Ariz. 2010)"],
        "dist",
        "2010-12-08",
    ),
    # State-court citing references for Martinez and Hernandez Pomona
    9100213: external_op(
        9100213,
        "Hartman v. State",
        "98-CC-12345",
        ["8 N.Y.3d 542"],
        "ny",
        "2007-05-08",
    ),
    9100214: external_op(
        9100214,
        "Robinson v. County of Los Angeles",
        "S180404",
        ["50 Cal. 4th 1078"],
        "cal",
        "2010-08-12",
    ),
    # An older case A questioned by another scoped case (for "as recognized by")
    9920001: external_op(
        9920001,
        "Brown v. State of New York",
        "BRN-1996",
        ["89 N.Y.2d 172", "674 N.E.2d 1129"],
        "ny",
        "1996-11-19",
    ),
    # District court that cites Pearson heavily — populate cited_by
    9920003: external_op(
        9920003,
        "Doe v. City of Boston",
        "11-cv-12011",
        ["No. 11-12011 (D. Mass. 2014)"],
        "dist",
        "2014-03-19",
    ),
    9920004: external_op(
        9920004,
        "Roe v. Phoenix Police Dept.",
        "13-cv-00214",
        ["No. CV-13-0214 (D. Ariz. 2015)"],
        "dist",
        "2015-08-20",
    ),
    # ── Citing references for the lower-court opinions ─────────────────
    # Cited by Callahan v. Millard County (10th Cir. 2007)
    9920010: external_op(
        9920010,
        "Saavedra v. Murphy",
        "13-4022",
        ["739 F.3d 1273"],
        "ca10",
        "2014-01-21",
    ),
    9920011: external_op(
        9920011,
        "Romero v. Story",
        "11-2157",
        ["672 F.3d 880"],
        "ca10",
        "2012-03-12",
    ),
    9920012: external_op(
        9920012,
        "Yang v. Boulder Police Dept.",
        "16-cv-00821",
        ["No. 16-cv-821 (D. Colo. 2018)"],
        "dist",
        "2018-04-30",
    ),
    9920013: external_op(
        9920013,
        "Bishop v. Hackel",
        "10-1335",
        ["636 F.3d 757"],
        "ca6",
        "2011-03-21",
    ),
    9920014: external_op(
        9920014,
        "Riggs v. Carbon County",
        "18-4031",
        ["920 F.3d 752"],
        "ca10",
        "2019-03-19",
    ),
    # Cited by Henry v. Purnell (4th Cir. 2011 en banc)
    9920020: external_op(
        9920020,
        "Estate of Armstrong v. Pinehurst",
        "15-1191",
        ["810 F.3d 892"],
        "ca4",
        "2016-01-11",
    ),
    9920021: external_op(
        9920021,
        "Wilson v. Prince George's County",
        "16-2052",
        ["893 F.3d 213"],
        "ca4",
        "2018-06-21",
    ),
    9920022: external_op(
        9920022,
        "Pollard v. Maryland State Police",
        "14-cv-02314",
        ["No. JKB-14-2314 (D. Md. 2017)"],
        "dist",
        "2017-09-12",
    ),
    9920023: external_op(
        9920023,
        "Anderson v. NYC Police Dept.",
        "12-3450",
        ["705 F.3d 65"],
        "ca2",
        "2013-04-22",
    ),
    9920024: external_op(
        9920024,
        "Mayfield v. Roanoke County",
        "12-1772",
        ["723 F.3d 433"],
        "ca4",
        "2013-07-15",
    ),
    # Cited by Maldonado v. Fontanes (1st Cir. 2009)
    9920030: external_op(
        9920030,
        "Pearson Educ., Inc. v. Liu",
        "11-cv-12345",
        ["No. 11-12345 (D.P.R. 2013)"],
        "dist",
        "2013-06-18",
    ),
    9920031: external_op(
        9920031,
        "Garcia v. Municipality of Carolina",
        "12-1456",
        ["692 F.3d 7"],
        "ca1",
        "2012-09-04",
    ),
    9920032: external_op(
        9920032,
        "Estrada v. Rhode Island",
        "16-1567",
        ["832 F.3d 39"],
        "ca1",
        "2016-08-15",
    ),
    # Cited by Lacey v. Arpaio (9th Cir. 2012 en banc)
    9920040: external_op(
        9920040,
        "Ballentine v. Tucker",
        "16-15672",
        ["881 F.3d 597"],
        "ca9",
        "2018-01-08",
    ),
    9920041: external_op(
        9920041,
        "Skoog v. County of Clackamas",
        "13-35451",
        ["744 F.3d 1198"],
        "ca9",
        "2014-03-21",
    ),
    9920042: external_op(
        9920042,
        "Doe v. Maricopa County",
        "15-cv-00789",
        ["No. CV-15-789 (D. Ariz. 2017)"],
        "dist",
        "2017-11-04",
    ),
    # Cited by Hernandez v. City of Pomona (Cal. 2009)
    9920050: external_op(
        9920050,
        "Hayes v. County of San Diego",
        "S193997",
        ["57 Cal. 4th 622"],
        "cal",
        "2013-08-19",
    ),
    9920051: external_op(
        9920051,
        "Adams v. City of Fremont",
        "A123456",
        ["68 Cal. App. 4th 243"],
        "cal",
        "2012-05-14",
    ),
    # Cited by Martinez v. City of Schenectady (NY 2001)
    9920060: external_op(
        9920060,
        "Lyles v. State",
        "OD-2009-12",
        ["13 N.Y.3d 312"],
        "ny",
        "2009-10-22",
    ),
    9920061: external_op(
        9920061,
        "Williams v. State of New York",
        "OD-2014-04",
        ["22 N.Y.3d 423"],
        "ny",
        "2014-04-29",
    ),
    # Cited by D. Utah Callahan (fictional, 2005)
    9920070: external_op(
        9920070,
        "Walker v. Salt Lake City",
        "08-cv-00567",
        ["No. 2:08-cv-00567 (D. Utah 2010)"],
        "utd",
        "2010-07-15",
    ),
    9920071: external_op(
        9920071,
        "Reed v. Cottonwood Heights",
        "11-cv-00123",
        ["No. 2:11-cv-00123 (D. Utah 2013)"],
        "utd",
        "2013-02-19",
    ),
}


# ── EDGES — single source of truth for treatment relationships ─────────
# Each edge says: citing cluster applied `treatment` to cited cluster.
# build_data.py expands these into per-opinion authorities[] / cited_by[]
# views.
EDGES = [
    # ── Direct History: 10th Cir. Callahan -> D. Utah Callahan -- AFFIRMED
    edge(
        citing_cluster_id=1425860,
        cited_cluster_id=9999001,
        treatment="Affirmed by",
        quote="Holding that the district court was correct in its determination that Mr. Callahan's constitutional rights were violated",
        rationale="Direct procedural history: 10th Cir. affirmed lower court's constitutional-violation finding (reversed only on the clearly-established prong).",
        section_context="Holding that the district court was correct in its determination that Mr. Callahan's constitutional rights were violated, but incorrect in its determination that these rights were not clearly established, we reverse in part and remand.",
        source="expert",
    ),
    # ── Direct History: Pearson -> Callahan-10th -- REVERSED
    edge(
        citing_cluster_id=145918,
        cited_cluster_id=1425860,
        treatment="Reversed by",
        quote="we reverse and remand for further proceedings consistent with this opinion",
        rationale="Direct procedural history: SCOTUS reversed 10th Cir. denial of QI.",
        section_context="On appeal, a divided panel of the Tenth Circuit held that petitioners' conduct violated respondent's Fourth Amendment rights. Callahan v. Millard Cty., 494 F. 3d 891 (2007). For the reasons set forth above, we reverse and remand for further proceedings consistent with this opinion.",
        source="expert",
    ),
    # ── Direct History: Fabricated SCOTUS affirmance of Henry v. Purnell
    edge(
        citing_cluster_id=9999002,
        cited_cluster_id=220962,
        treatment="Affirmed by",
        quote="the judgment of the Court of Appeals is affirmed",
        rationale="Direct procedural history: SCOTUS (mock) affirmed 4th Cir. en banc denial of QI.",
        section_context="On the question presented, the judgment of the Court of Appeals is affirmed. The officer's use of deadly force violated clearly established law.",
        source="model",
    ),
    # ── Pearson modifies Saucier (self court_relationship)
    edge(
        citing_cluster_id=145918,
        cited_cluster_id=118449,
        treatment="Limited by",
        quote="the Saucier procedure should not be regarded as an inflexible requirement",
        rationale="Pearson held Saucier's mandatory two-step ordering is no longer required.",
        section_context="We now hold that the Saucier procedure should not be regarded as an inflexible requirement and that petitioners are entitled to qualified immunity on the ground that it was not clearly established at the time of the search that their conduct was unconstitutional. We therefore reverse.",
        source="expert",
    ),
    # ── Pearson cites Harlow
    edge(
        citing_cluster_id=145918,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote="The doctrine of qualified immunity protects government officials",
        rationale="Pearson cites Harlow for the canonical QI standard.",
        section_context='The doctrine of qualified immunity protects government officials "from liability for civil damages insofar as their conduct does not violate clearly established statutory or constitutional rights of which a reasonable person would have known." Harlow v. Fitzgerald, 457 U. S. 800, 818 (1982).',
        source="model",
    ),
    # ── Saucier cites Harlow
    edge(
        citing_cluster_id=118449,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote="avoid excessive disruption of government and permit the resolution of many insubstantial claims on summary judgment",
        rationale="Saucier cites Harlow's policy rationale.",
        section_context='The approach the Court of Appeals adopted could undermine the goal of qualified immunity to "avoid excessive disruption of government and permit the resolution of many insubstantial claims on summary judgment." Harlow v. Fitzgerald, 457 U. S. 800, 818 (1982).',
        source="model",
    ),
    # ── Callahan-10th cites Saucier (applies the two-step)
    edge(
        citing_cluster_id=1425860,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="If no constitutional right would have been violated were the allegations established",
        rationale="10th Cir. applies Saucier's mandatory two-step.",
        section_context="If no constitutional right would have been violated were the allegations established, there is no necessity for further inquiries concerning qualified immunity — quoting Saucier v. Katz, 533 U.S. 194, 201 (2001). If the plaintiff establishes that a constitutional right was violated, then the plaintiff must also show that the violated right was clearly established.",
        source="model",
    ),
    # ── D. Utah Callahan cites Saucier
    edge(
        citing_cluster_id=9999001,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="the two-step inquiry set out by the Supreme Court",
        rationale="District court applies Saucier's two-step.",
        section_context="The applicable framework is the two-step inquiry set out by the Supreme Court in Saucier v. Katz, 533 U.S. 194 (2001), governed in this Circuit by the gloss our Court of Appeals applied in earlier cases.",
        source="model",
    ),
    # ── Henry v. Purnell cites Saucier (recognizing modification by Pearson)
    edge(
        citing_cluster_id=220962,
        cited_cluster_id=118449,
        treatment="Limited as recognized by",
        quote="Saucier v. Katz, 533 U.S. 194, 206 (2001), overruled in part",
        rationale='Henry recognizes Pearson modified Saucier ("as recognized by" / Related Reference).',
        section_context="Saucier v. Katz, 533 U.S. 194, 206 (2001), overruled in part, Pearson v. Callahan, 129 S. Ct. 808 (2009). Following the Supreme Court's recent decision in Pearson, we exercise our discretion to use the two-step procedure of Saucier.",
        source="expert",
    ),
    # ── Henry v. Purnell cites Pearson (the case that modified Saucier)
    edge(
        citing_cluster_id=220962,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="Following the Supreme Court's recent decision in Pearson",
        rationale="Henry cites Pearson as the modifying authority.",
        section_context="Following the Supreme Court's recent decision in Pearson, we exercise our discretion to use the two-step procedure of Saucier, that asks first whether a constitutional violation occurred and second whether the right violated was clearly established.",
        source="model",
    ),
    # ── Henry cites Harlow
    edge(
        citing_cluster_id=220962,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote="a test that focuses on the objective legal reasonableness",
        rationale="Henry cites Harlow's objective-reasonableness articulation.",
        section_context='The second prong is "a test that focuses on the objective legal reasonableness of an official\'s acts." Harlow v. Fitzgerald, 457 U.S. 800, 819 (1982).',
        source="model",
    ),
    # ── Maldonado cites Pearson
    edge(
        citing_cluster_id=203857,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="Pearson also held that while it is frequently appropriate for courts to answer each step in turn, it is not mandatory",
        rationale="Maldonado applies Pearson's permissive sequencing rule.",
        section_context="Pearson also held that while it is frequently appropriate for courts to answer each step in turn, it is not mandatory that courts follow the two-step analysis sequentially. Courts have discretion to decide whether, on the facts of a particular case, it is worthwhile to address first whether the facts alleged make out a violation of a constitutional right.",
        source="model",
    ),
    # ── Maldonado cites Saucier
    edge(
        citing_cluster_id=203857,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="the salient question is whether the state of the law at the time of the alleged violation gave the defendant fair warning",
        rationale="Maldonado cites Saucier's clearly-established formulation.",
        section_context="The relevant, dispositive inquiry in determining whether a right is clearly established is whether it would be clear to a reasonable officer that his conduct was unlawful in the situation he confronted — quoting Saucier v. Katz, 533 U.S. at 202.",
        source="model",
        expert_treatment="Distinguished by",
    ),
    # ── Lacey cites Pearson
    edge(
        citing_cluster_id=807646,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="We have the discretion to decide which of the two prongs of the qualified immunity analysis should be addressed first",
        rationale="Lacey applies Pearson's discretionary ordering rule.",
        section_context="We have the discretion to decide which of the two prongs of the qualified immunity analysis should be addressed first in light of the circumstances in the particular case at hand. Pearson, 555 U.S. at 236.",
        source="model",
    ),
    # ── Lacey cites Saucier
    edge(
        citing_cluster_id=807646,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="we ask whether the facts alleged show the officer's conduct violated a constitutional right",
        rationale="Lacey applies Saucier's first prong.",
        section_context="Determining whether a defendant is entitled to qualified immunity involves a two-pronged analysis. First, we ask whether the facts alleged show the officer's conduct violated a constitutional right — Saucier v. Katz, 533 U.S. 194, 201 (2001), overruled in part by Pearson, 555 U.S. at 235–236.",
        source="model",
    ),
    # ── Lacey cites Harlow
    edge(
        citing_cluster_id=807646,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote='Qualified immunity "represents the norm" for government officials',
        rationale="Lacey cites Harlow as foundational QI authority.",
        section_context='Qualified immunity "represents the norm" for government officials exercising discretionary authority, Harlow v. Fitzgerald, 457 U.S. 800, 807 (1982), including prosecutors who are not acting as an advocate for the state and may not be entitled to absolute immunity.',
        source="model",
    ),
    # ── Sister-circuit edge: Lacey distinguishes Maldonado
    edge(
        citing_cluster_id=807646,
        cited_cluster_id=203857,
        treatment="Distinguished by",
        quote="The First Circuit's analysis in Maldonado v. Fontanes addressed substantive due process claims",
        rationale="Sister-circuit (horizontal_persuasive) — Lacey distinguishes Maldonado on factual posture.",
        section_context="The First Circuit's analysis in Maldonado v. Fontanes addressed substantive due process claims with no allegation of First Amendment retaliation. Here, Lacey's claims are anchored in retaliation for newsgathering, a context Maldonado did not consider.",
        source="model",
    ),
    # ── Martinez (NY) cites Saucier
    edge(
        citing_cluster_id=2219834,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="qualified immunity barred the assertion of the section 1983 claims",
        rationale="NY Court of Appeals notes federal QI ruling.",
        section_context="The United States Court of Appeals for the Second Circuit reversed the denial of defendants' summary judgment motion, concluding as a matter of law that qualified immunity barred the assertion of the section 1983 claims against the police officers, applying the framework set out by the Supreme Court in Saucier v. Katz.",
        source="model",
    ),
    # ── Martinez (NY) cites Brown v. State of New York (Questioned)
    edge(
        citing_cluster_id=2219834,
        cited_cluster_id=9920001,
        treatment="Distinguished by",
        quote='the "narrow remedy" established in Brown v. State of New York cannot be stretched',
        rationale="Martinez distinguishes Brown's state-constitutional tort remedy.",
        section_context='We agree with Supreme Court and the Appellate Division that the "narrow remedy" established in Brown v. State of New York (89 NY2d 172, 192 [1996]) cannot be stretched to fit the facts before us.',
        source="model",
    ),
    # ── Hernandez Pomona (CA) cites Saucier
    edge(
        citing_cluster_id=1801687,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="high court precedent required the trial court first to decide whether Sanchez had violated Hernandez's constitutional rights",
        rationale="Cal. Sup. Ct. notes Saucier's mandatory ordering at the time of trial.",
        section_context="At the time of the federal trial, high court precedent required the trial court first to decide whether Sanchez had violated Hernandez's constitutional rights, and then to decide the immunity question — Saucier v. Katz (2001) 533 U.S. 194, 201.",
        source="model",
    ),
    # ── Hernandez Pomona (CA) cites Pearson
    edge(
        citing_cluster_id=1801687,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="The high court recently changed this rule, holding that trial courts may decide the immunity question",
        rationale="Cal. Sup. Ct. acknowledges Pearson's change to the ordering rule.",
        section_context="The high court recently changed this rule, holding that trial courts may decide the immunity question before (or without) determining whether there was a constitutional violation — Pearson v. Callahan (2009) 555 U.S. ___.",
        source="expert",
    ),
    # ── Sister-state edge: Hernandez Pomona cites Martinez
    edge(
        citing_cluster_id=1801687,
        cited_cluster_id=2219834,
        treatment="Cited by",
        quote="the New York Court of Appeals confronted a similar preclusion question",
        rationale="Sister-state (horizontal_persuasive) — Cal. Sup. Ct. cites NY Court of Appeals as persuasive authority on §1983 preclusion.",
        section_context="In Martinez v. City of Schenectady, 97 N.Y.2d 78 (2001), the New York Court of Appeals confronted a similar preclusion question and declined to extend the state constitutional tort remedy where federal courts had already resolved the underlying §1983 claim on qualified-immunity grounds.",
        source="model",
    ),
    # ── External edges — non-scoped citing/cited cases (populate cited_by)
    # Reichle v. Howards cites Pearson
    edge(
        citing_cluster_id=9100201,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="we follow the discretionary sequencing established in Pearson",
        rationale="SCOTUS post-Pearson case applying its rule.",
        section_context="In analyzing the qualified-immunity defense, we follow the discretionary sequencing established in Pearson v. Callahan, 555 U.S. 223 (2009), which permits us to address the clearly-established prong without first deciding the constitutional question.",
        source="model",
    ),
    # Plumhoff cites Saucier
    edge(
        citing_cluster_id=9100202,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="we apply the two-step framework articulated in Saucier",
        rationale="SCOTUS QI case applying Saucier framework.",
        section_context="In addressing the officers' qualified-immunity defense, we apply the two-step framework articulated in Saucier v. Katz, 533 U.S. 194 (2001), as modified by Pearson v. Callahan.",
        source="model",
    ),
    # Mullenix v. Luna criticizes the lower court's Pearson application
    edge(
        citing_cluster_id=9100203,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="Pearson did not require the Fifth Circuit to address the constitutional question",
        rationale="SCOTUS reverses 5th Cir. for not heeding Pearson's discretionary sequencing.",
        section_context="Although Pearson did not require the Fifth Circuit to address the constitutional question, the lower court chose to do so and reached an erroneous conclusion. We need not address that error today.",
        source="model",
    ),
    # Hernandez v. Mesa cites Pearson
    edge(
        citing_cluster_id=9100204,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="our discretion to address either prong of the qualified-immunity inquiry first",
        rationale="SCOTUS Bivens / cross-border shooting case applying Pearson sequencing.",
        section_context="Consistent with Pearson v. Callahan, 555 U.S. 223 (2009), we exercise our discretion to address either prong of the qualified-immunity inquiry first.",
        source="model",
    ),
    # Brosseau v. Haugen cites Saucier
    edge(
        citing_cluster_id=9100205,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="the second step of the qualified immunity analysis must be undertaken in light of the specific context",
        rationale="Pre-Pearson per-curiam SCOTUS case applying Saucier framework.",
        section_context="As we explained in Saucier, the second step of the qualified immunity analysis must be undertaken in light of the specific context of the case, not as a broad general proposition.",
        source="model",
    ),
    # Scott v. Harris cites Saucier
    edge(
        citing_cluster_id=9100206,
        cited_cluster_id=118449,
        treatment="Cited by",
        quote="we follow the order of analysis Saucier prescribed",
        rationale="SCOTUS pre-Pearson; mandatory two-step still good law at the time.",
        section_context="In assessing qualified immunity, we follow the order of analysis Saucier prescribed: first whether a constitutional right would have been violated, and second whether the right was clearly established.",
        source="model",
    ),
    # Anderson v. Creighton cites Harlow
    edge(
        citing_cluster_id=9100207,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote="The contours of the right must be sufficiently clear",
        rationale="Anderson refines Harlow's clearly-established standard.",
        section_context="The contours of the right must be sufficiently clear that a reasonable official would understand that what he is doing violates that right — extending Harlow v. Fitzgerald's articulation of the qualified-immunity inquiry.",
        source="expert",
    ),
    # Wilson v. Layne cites Harlow
    edge(
        citing_cluster_id=9100208,
        cited_cluster_id=110763,
        treatment="Cited by",
        quote="the clearly-established analysis is conducted by reference to existing precedent",
        rationale="Wilson applies Harlow's clearly-established framework.",
        section_context="As Harlow v. Fitzgerald instructs, the clearly-established analysis is conducted by reference to existing precedent at the time of the conduct.",
        source="model",
    ),
    # Henry v. Purnell (4th Cir. en banc) reversed D. Md. district court
    edge(
        citing_cluster_id=220962,
        cited_cluster_id=9100210,
        treatment="Reversed by",
        quote="we reverse and remand",
        rationale="Direct history: 4th Cir. en banc reversed district court's grant of QI.",
        section_context="The decision of the district court is REVERSED AND REMANDED. Purnell's use of deadly force against Henry was objectively unreasonable and violated clearly established law.",
        source="expert",
    ),
    # Maldonado v. Fontanes (1st Cir.) affirmed D.P.R. denial of QI
    edge(
        citing_cluster_id=203857,
        cited_cluster_id=9100211,
        treatment="Affirmed by",
        quote="We affirm the denial of the Mayor's motion for qualified immunity",
        rationale="Direct history: 1st Cir. affirmed district court's denial of QI on Fourth Amendment / procedural due process claims.",
        section_context="We affirm the denial of the Mayor's motion for qualified immunity on the Fourth Amendment and Fourteenth Amendment procedural due process claims, and reverse on the substantive due process claim.",
        source="expert",
    ),
    # Lacey v. Arpaio (9th Cir. en banc) affirmed-in-part / reversed-in-part D. Ariz.
    edge(
        citing_cluster_id=807646,
        cited_cluster_id=9100212,
        treatment="Affirmed in part; Reversed in part by",
        quote="We affirm in part and reverse in part",
        rationale="Direct history: 9th Cir. en banc affirmed dismissal of some claims, reversed dismissal of others.",
        section_context="We affirm in part and reverse in part, finding that Lacey adequately alleged several causes of action for which the defendants are not entitled to immunity. We remand for further proceedings.",
        source="model",
    ),
    # Hartman v. State (NY) cites Martinez
    edge(
        citing_cluster_id=9100213,
        cited_cluster_id=2219834,
        treatment="Cited by",
        quote="this Court declined in Martinez to extend the Brown remedy",
        rationale="Later NY Court of Appeals case citing Martinez on state constitutional torts.",
        section_context="As this Court declined in Martinez v. City of Schenectady to extend the Brown remedy where the underlying federal claim had been resolved on qualified-immunity grounds, we similarly decline here.",
        source="model",
    ),
    # Robinson v. County of Los Angeles cites Hernandez Pomona
    edge(
        citing_cluster_id=9100214,
        cited_cluster_id=1801687,
        treatment="Cited by",
        quote="our decision in Hernandez v. City of Pomona controls the preclusion analysis",
        rationale="Later Cal. Sup. Ct. case applying Hernandez Pomona's preclusion holding.",
        section_context="As we held in Hernandez v. City of Pomona, 46 Cal. 4th 501 (2009), our decision controls the preclusion analysis where the federal court has resolved the §1983 claim on qualified-immunity grounds.",
        source="model",
    ),
    # Susag v. Lake Forest (Ca App) cites Hernandez Pomona — wait, this is pre-2009. Skip.
    # Doe v. Boston cites Pearson
    edge(
        citing_cluster_id=9920003,
        cited_cluster_id=145918,
        treatment="Cited by",
        quote="Pearson permits courts to bypass the constitutional-violation prong",
        rationale="District court applies Pearson sequencing.",
        section_context="Pearson v. Callahan permits courts to bypass the constitutional-violation prong and resolve the qualified-immunity defense on the clearly-established prong alone.",
        source="model",
    ),
    # Roe v. Phoenix Police cites Lacey (intra-9th-Cir district application)
    edge(
        citing_cluster_id=9920004,
        cited_cluster_id=807646,
        treatment="Cited by",
        quote="Lacey v. Arpaio is binding authority on First Amendment retaliation claims",
        rationale="District court within 9th Cir. applies Lacey.",
        section_context="In this Circuit, Lacey v. Arpaio is binding authority on First Amendment retaliation claims arising from law-enforcement conduct.",
        source="model",
        expert_treatment="Distinguished by",
    ),
    # ── Citing references TO lower-court opinions ─────────────────────
    # These give the lower-court opinion pages enough non-direct
    # cited_by content to populate "Most negative" / "Most recent
    # negative" cards alongside the Direct history card.
    # Citing references to Callahan v. Millard County (10th Cir. 2007)
    edge(
        citing_cluster_id=9920010,
        cited_cluster_id=1425860,
        treatment="Limited by",
        quote="the consent-once-removed analysis in Callahan must be read narrowly post-Pearson",
        rationale="Later 10th Cir. case limits Callahan's scope after Pearson reframed the QI inquiry.",
        section_context="As we observed before, the consent-once-removed analysis in Callahan must be read narrowly post-Pearson; the rule does not extend to circumstances where the informant lacks ongoing authority to admit additional officers.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920011,
        cited_cluster_id=1425860,
        treatment="Distinguished by",
        quote="Callahan addressed a controlled drug-buy posture not present here",
        rationale="Sister 10th Cir. panel distinguishes on facts.",
        section_context="The plaintiff relies on our decision in Callahan v. Millard County, but Callahan addressed a controlled drug-buy posture not present here. The officers in this case entered without an antecedent invitation by an authorized resident.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920012,
        cited_cluster_id=1425860,
        treatment="Cited by",
        quote="we follow the framework laid out in Callahan",
        rationale="Within-circuit district court applies Callahan's framework.",
        section_context="In analyzing the consent-once-removed defense, we follow the framework laid out in Callahan v. Millard County, 494 F.3d 891 (10th Cir. 2007), with the subsequent gloss our circuit has applied.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920013,
        cited_cluster_id=1425860,
        treatment="Declined to follow by",
        quote="we decline to adopt the consent-once-removed expansion endorsed by the Tenth Circuit in Callahan",
        rationale="Sister-circuit (6th Cir., horizontal_persuasive) declines to follow the 10th Cir. rule.",
        section_context="Although our sister Circuit reached the opposite conclusion, we decline to adopt the consent-once-removed expansion endorsed by the Tenth Circuit in Callahan v. Millard County. The doctrine, as applied there, runs afoul of the Fourth Amendment's clear textual demand for warrant-based entry.",
        source="expert",
    ),
    edge(
        citing_cluster_id=9920014,
        cited_cluster_id=1425860,
        treatment="Distinguished by",
        quote="the consent-once-removed analysis in Callahan does not extend to the present facts",
        rationale="Recent 10th Cir. case distinguishing — gives Callahan a divergent most-recent vs most-severe.",
        section_context="The defendants invoke our prior decision in Callahan v. Millard County, but the consent-once-removed analysis in Callahan does not extend to the present facts. Here, no antecedent invitation gave the officers any color of authorization to enter.",
        source="model",
    ),
    # Citing references to Henry v. Purnell (4th Cir. 2011 en banc)
    edge(
        citing_cluster_id=9920020,
        cited_cluster_id=220962,
        treatment="Cited by",
        quote="our en banc decision in Henry v. Purnell",
        rationale="Within-circuit follow-on; applies Henry's deadly-force / Garner standard.",
        section_context="In assessing the officer's use of force, we apply the framework set out in our en banc decision in Henry v. Purnell, 652 F.3d 524 (4th Cir. 2011), which controls Fourth-Amendment excessive-force claims involving fleeing suspects.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920021,
        cited_cluster_id=220962,
        treatment="Distinguished by",
        quote="Henry involved a stipulated mistake about the weapon used; here the officer concedes no mistake",
        rationale="Within-circuit panel distinguishes on the stipulated-fact posture.",
        section_context="The plaintiff's reliance on Henry v. Purnell is misplaced: Henry involved a stipulated mistake about the weapon used; here the officer concedes no mistake. Henry's qualified-immunity ruling thus does not control.",
        source="model",
        expert_treatment="Cited by",
    ),
    edge(
        citing_cluster_id=9920022,
        cited_cluster_id=220962,
        treatment="Cited by",
        quote="applying Henry v. Purnell's deadly-force framework",
        rationale="Within-circuit district court applies Henry.",
        section_context="In applying Henry v. Purnell's deadly-force framework, the Court considers whether a reasonable officer in the defendant's position would have understood that lethal force was unjustified under the totality of the circumstances.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920023,
        cited_cluster_id=220962,
        treatment="Criticized by",
        quote="we are unable to reconcile the result in Henry v. Purnell with the Supreme Court's framework",
        rationale="Sister-circuit (2nd Cir., horizontal_persuasive) criticizes the en banc result.",
        section_context="With respect to our colleagues on the Fourth Circuit, we are unable to reconcile the result in Henry v. Purnell with the Supreme Court's framework for evaluating mistaken-belief uses of force. The objective-reasonableness inquiry should foreclose, not invite, second-guessing under the conditions there.",
        source="expert",
    ),
    edge(
        citing_cluster_id=9920024,
        cited_cluster_id=220962,
        treatment="Limited by",
        quote="Henry's holding is limited to the stipulated mistake-of-weapon scenario",
        rationale="Earlier within-circuit case narrows Henry's reach — gives Henry a divergent most-severe vs most-recent.",
        section_context="As we have observed before, Henry's holding is limited to the stipulated mistake-of-weapon scenario. The court's analysis of objective unreasonableness was driven by that stipulated factual posture and does not generalize to ordinary deadly-force claims.",
        source="model",
    ),
    # Citing references to Maldonado v. Fontanes (1st Cir. 2009)
    edge(
        citing_cluster_id=9920030,
        cited_cluster_id=203857,
        treatment="Cited by",
        quote="we follow Maldonado v. Fontanes's articulation of the post-Pearson sequencing rule",
        rationale="Within-circuit district court applies Maldonado.",
        section_context="In addressing the qualified-immunity defense, we follow Maldonado v. Fontanes's articulation of the post-Pearson sequencing rule, exercising discretion to decide which prong to address first.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920031,
        cited_cluster_id=203857,
        treatment="Distinguished by",
        quote="Maldonado involved a substantive due process claim; the present case is grounded entirely in Fourth Amendment seizure doctrine",
        rationale="Within-circuit panel distinguishes on the underlying constitutional claim.",
        section_context="The plaintiff invokes our holding in Maldonado v. Fontanes, but that case is inapposite here. Maldonado involved a substantive due process claim; the present case is grounded entirely in Fourth Amendment seizure doctrine.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920032,
        cited_cluster_id=203857,
        treatment="Limited by",
        quote="Maldonado's broader procedural-due-process holding has been narrowed",
        rationale="Within-circuit later panel limits Maldonado.",
        section_context="To the extent that prior dicta suggested a more expansive procedural-due-process remedy, Maldonado's broader procedural-due-process holding has been narrowed by intervening decisions of the Supreme Court.",
        source="model",
    ),
    # Citing references to Lacey v. Arpaio (9th Cir. 2012 en banc)
    edge(
        citing_cluster_id=9920040,
        cited_cluster_id=807646,
        treatment="Distinguished by",
        quote="Lacey involved a high-profile arrest of journalists for newsgathering activity",
        rationale="Within-circuit panel distinguishes on the journalism context.",
        section_context="The plaintiff relies on Lacey v. Arpaio, but Lacey involved a high-profile arrest of journalists for newsgathering activity. The First Amendment retaliation claim there arose from a categorically different context than the routine traffic stop at issue here.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920041,
        cited_cluster_id=807646,
        treatment="Cited by",
        quote="our en banc decision in Lacey v. Arpaio",
        rationale="Within-circuit follow-on applying Lacey's First Amendment retaliation framework.",
        section_context="As reaffirmed in our en banc decision in Lacey v. Arpaio, 693 F.3d 896 (9th Cir. 2012), retaliatory law-enforcement actions targeted at protected speech remain actionable under §1983.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920042,
        cited_cluster_id=807646,
        treatment="Cited by",
        quote="Lacey v. Arpaio governs First Amendment retaliation analysis in this Circuit",
        rationale="Within-circuit district court applies Lacey.",
        section_context="Lacey v. Arpaio governs First Amendment retaliation analysis in this Circuit, and we apply its framework to evaluate the plaintiff's claim that her arrest was retaliatory.",
        source="model",
    ),
    # Citing references to Hernandez v. City of Pomona (Cal. 2009)
    edge(
        citing_cluster_id=9920050,
        cited_cluster_id=1801687,
        treatment="Distinguished by",
        quote="Hernandez addressed preclusion arising from a federal qualified-immunity ruling",
        rationale="Same court (Cal. Supreme self-citation) distinguishes on procedural posture.",
        section_context="The defendants invoke our preclusion analysis in Hernandez v. City of Pomona, but the procedural posture here is different. Hernandez addressed preclusion arising from a federal qualified-immunity ruling; here, the underlying federal action was dismissed without prejudice on jurisdictional grounds.",
        source="expert",
    ),
    edge(
        citing_cluster_id=9920051,
        cited_cluster_id=1801687,
        treatment="Cited by",
        quote="Hernandez v. City of Pomona controls the issue-preclusion analysis",
        rationale="State appellate court applies Hernandez.",
        section_context="Where the federal court has resolved an excessive-force §1983 claim on qualified-immunity grounds, our Supreme Court's decision in Hernandez v. City of Pomona, 46 Cal. 4th 501 (2009), controls the issue-preclusion analysis.",
        source="model",
    ),
    # Citing references to Martinez v. City of Schenectady (NY 2001)
    edge(
        citing_cluster_id=9920060,
        cited_cluster_id=2219834,
        treatment="Distinguished by",
        quote="Martinez involved a federal qualified-immunity ruling that triggered preclusion",
        rationale="Same court distinguishes on procedural posture.",
        section_context="The defendants point to Martinez v. City of Schenectady, but Martinez involved a federal qualified-immunity ruling that triggered preclusion of the state constitutional tort claim. The present plaintiff faced no parallel federal proceeding.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920061,
        cited_cluster_id=2219834,
        treatment="Limited by",
        quote="Martinez's preclusion holding does not extend beyond the search-warrant context",
        rationale="Same court (NY Court of Appeals) narrows Martinez.",
        section_context="To the extent later decisions have read Martinez expansively, we now clarify that Martinez's preclusion holding does not extend beyond the search-warrant context. The state-constitutional remedy remains available where the federal claim turns on different operative facts.",
        source="model",
        expert_treatment="Distinguished by",
    ),
    # Citing references to D. Utah Callahan (fictional district court, 2005)
    edge(
        citing_cluster_id=9920070,
        cited_cluster_id=9999001,
        treatment="Distinguished by",
        quote="the district court's analysis in Callahan v. Millard County Sheriff turned on the consent-once-removed posture",
        rationale="Later D. Utah opinion distinguishes on facts.",
        section_context="The plaintiff's reliance on the district court's analysis in Callahan v. Millard County Sheriff turned on the consent-once-removed posture, which is not present here. We need not address whether the framework articulated there has survived Pearson's reframing of the qualified-immunity inquiry.",
        source="model",
    ),
    edge(
        citing_cluster_id=9920071,
        cited_cluster_id=9999001,
        treatment="Cited by",
        quote="the consent-once-removed framework outlined in Callahan v. Millard County Sheriff",
        rationale="Within-court (D. Utah) cites for fact-bound analysis.",
        section_context="In applying the consent-once-removed framework outlined in Callahan v. Millard County Sheriff, we consider whether the antecedent invitation extended to subsequent law-enforcement entry under the totality of the circumstances.",
        source="model",
    ),
]
