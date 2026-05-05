"""Hand-written mock fixtures for the demo site, used until real inference
data lands (issue #13).

Uses the 10 real cluster IDs + case names from
ai-research/experiments_05012026/ so the real-data swap is "replace this
module's MOCK_OPINIONS with a function that reads CSVs from data-source/."

Treatments and validation states are fabricated to exercise every UX state.

Cross-references intentionally seeded:
- Hernández v. Mesa (4729777, 2020)   cites    Allen v. McCurry (110360)
- Sanchez ex rel. DR-S. (622781)      cites    Allen v. McCurry (110360)
- Allen v. McCurry (110360)            cited by Hernández + Sanchez
"""

from __future__ import annotations

# ── Scoped-in cluster IDs ──────────────────────────────────────────────
SCOPED_CLUSTER_IDS = frozenset({
    110274,    # Walker v. Armco Steel Corp.
    110360,    # Allen v. McCurry
    4729777,   # Hernández v. Mesa
    117927,    # United States v. Lopez
    145643,    # Empire Healthchoice v. McVeigh
    725046,    # United States v. Felix Garcia (ca2)
    527778,    # In Re Stephen C. Perry (ca1)
    201580,    # Narragansett Indian v. State of Rhode Island (ca1)
    622781,    # Sanchez ex rel. DR-S. v. United States (ca1)
    1254,      # Chamberlin v. Town of Stoughton (ca1)
})

# ── Court display names ────────────────────────────────────────────────
COURT_DISPLAY = {
    "scotus": "U.S. Supreme Court",
    "ca1": "First Circuit",
    "ca2": "Second Circuit",
    "ca3": "Third Circuit",
    "ca4": "Fourth Circuit",
    "ca5": "Fifth Circuit",
    "ca6": "Sixth Circuit",
    "ca7": "Seventh Circuit",
    "ca8": "Eighth Circuit",
    "ca9": "Ninth Circuit",
    "ca10": "Tenth Circuit",
    "ca11": "Eleventh Circuit",
    "cadc": "D.C. Circuit",
    "cafc": "Federal Circuit",
    "dist": "U.S. District Court",
    "state": "State Court",
}


# ── Helper to make authority rows compact ──────────────────────────────
def auth(
    cited_cluster_id: int,
    cited_case_name: str,
    cited_citation: str,
    treatment: str,
    section_id: str,
    quote: str,
    rationale: str,
    validation_state: str = "unverified",
    expert_treatment: str | None = None,
) -> dict:
    return {
        "cited_cluster_id": cited_cluster_id,
        "cited_case_name": cited_case_name,
        "cited_citation": cited_citation,
        "treatment": treatment,
        "section_id": section_id,
        "quote": quote,
        "rationale": rationale,
        "validation_state": validation_state,
        "expert_treatment": expert_treatment,
    }


def cb(
    citing_cluster_id: int,
    citing_case_name: str,
    citing_citation: str,
    citing_court: str,
    citing_date_filed: str,
    treatment: str,
    quote: str,
    rationale: str,
    validation_state: str = "unverified",
    expert_treatment: str | None = None,
) -> dict:
    return {
        "citing_cluster_id": citing_cluster_id,
        "citing_case_name": citing_case_name,
        "citing_citation": citing_citation,
        "citing_court": citing_court,
        "citing_date_filed": citing_date_filed,
        "treatment": treatment,
        "quote": quote,
        "rationale": rationale,
        "validation_state": validation_state,
        "expert_treatment": expert_treatment,
    }


# ── 10 mock opinions ───────────────────────────────────────────────────
MOCK_OPINIONS = [
    {
        "cluster_id": 110274,
        "case_name": "Walker v. Armco Steel Corp.",
        "citation": "446 U.S. 740 (1980)",
        "court": "scotus",
        "date_filed": "1980-06-02",
        "document_text": """## I

The question presented is whether, in a diversity action, the federal court should follow state law or a Federal Rule of Civil Procedure in determining when an action is commenced for the purpose of tolling the state statute of limitations.

## II

Petitioner argues that Erie Railroad v. Tompkins <citedCase data-cluster-id="84759">Erie Railroad v. Tompkins</citedCase> requires application of the state rule. We disagree. The case is governed by the principles articulated in <citedCase data-cluster-id="103543">Hanna v. Plumer</citedCase>.

## III

Accordingly, the judgment of the Court of Appeals is affirmed.""",
        "authorities": [
            auth(84759, "Erie Railroad v. Tompkins", "304 U.S. 64", "Distinguished by", "II",
                 "the case is governed by the principles articulated in Hanna",
                 "Court is narrowing Erie's reach by drawing a distinction.",
                 "agree"),
            auth(103543, "Hanna v. Plumer", "380 U.S. 460", "Cited by", "II",
                 "applied the principles of Hanna v. Plumer",
                 "Standard cite-as-authority pattern.",
                 "unverified"),
            auth(85272, "M'Culloch v. Maryland", "17 U.S. 316", "Cited by", "I",
                 "as Chief Justice Marshall observed",
                 "Background reference.",
                 "agree"),
            auth(96276, "Lochner v. New York", "198 U.S. 45", "Distinguished by", "II",
                 "we decline to apply the reasoning of Lochner",
                 "Court distinguishes on substantive due process grounds.",
                 "disagree", "Cited by"),
            auth(85412, "Gibbons v. Ogden", "22 U.S. 1", "Cited by", "II",
                 "see Gibbons for the foundational analysis",
                 "Background only.",
                 "unverified"),
            auth(108085, "Pike v. Bruce Church, Inc.", "397 U.S. 137", "Cited by", "III",
                 "applying the Pike balancing test",
                 "Standard cite.",
                 "unverified"),
            auth(108375, "Bivens v. Six Unknown Named Agents", "403 U.S. 388", "Cited by", "II",
                 "noting the Bivens framework",
                 "Tangential mention.",
                 "unverified"),
            auth(110985, "INS v. Chadha", "462 U.S. 919", "Cited by", "III",
                 "see also Chadha",
                 "Cf. cite.",
                 "unverified"),
        ],
        "cited_by": [
            cb(9100001, "Smith v. Acme Manufacturing Co.", "812 F.3d 412", "ca5", "2016-04-12",
               "Cited by", "applying Walker v. Armco's reasoning",
               "Standard cite.", "unverified"),
            cb(9100002, "Doe v. State Farm Insurance Co.", "924 F.3d 988", "ca7", "2019-09-30",
               "Distinguished by", "We distinguish Walker on its facts; the procedural posture differs",
               "Court distinguishes correctly.", "agree"),
            cb(9100003, "United States v. Mitchell", "738 F.3d 1147", "ca4", "2014-01-08",
               "Cited by", "as Walker held",
               "Standard cite.", "unverified"),
            cb(9100004, "Brown v. Cumberland County", "452 F. Supp. 3d 89", "dist", "2020-03-15",
               "Affirmed in part; Reversed in part by", "the district court's reliance on Walker is misplaced in part",
               "Mixed disposition.", "agree"),
        ],
    },
    {
        "cluster_id": 110360,
        "case_name": "Allen v. McCurry",
        "citation": "449 U.S. 90 (1980)",
        "court": "scotus",
        "date_filed": "1980-12-09",
        "document_text": """## I

This case requires us to consider whether issue preclusion applies in a § 1983 action brought in federal court when the issue was previously litigated in a state criminal proceeding.

## II

Federal courts have traditionally adhered to the related doctrines of res judicata and collateral estoppel. See <citedCase data-cluster-id="85412">Gibbons v. Ogden</citedCase>. The doctrine serves the dual purpose of protecting litigants from the burden of relitigating an identical issue with the same party.

## III

We hold that collateral estoppel applies in § 1983 actions where the state court has provided a full and fair opportunity to litigate the issue.""",
        "authorities": [
            auth(85412, "Gibbons v. Ogden", "22 U.S. 1", "Cited by", "II",
                 "see Gibbons for the foundational doctrine",
                 "Background reference.", "unverified"),
            auth(108375, "Bivens v. Six Unknown Named Agents", "403 U.S. 388", "Cited by", "II",
                 "the doctrine that supports Bivens actions",
                 "Tangential.", "unverified"),
            auth(96276, "Lochner v. New York", "198 U.S. 45", "Cited by", "I",
                 "see Lochner",
                 "Cf cite.", "agree"),
            auth(105285, "Williamson v. Lee Optical of Oklahoma, Inc.", "348 U.S. 483", "Distinguished by", "III",
                 "we distinguish Williamson",
                 "Distinguishing on procedural grounds.", "agree"),
            auth(108085, "Pike v. Bruce Church, Inc.", "397 U.S. 137", "Cited by", "II",
                 "noted in Pike",
                 "Tangential cite.", "unverified"),
            auth(110985, "INS v. Chadha", "462 U.S. 919", "Cited by", "III",
                 "as Chadha makes clear",
                 "Standard cite.", "unverified"),
            auth(9200001, "Stone v. Powell", "428 U.S. 465", "Distinguished by", "II",
                 "Stone is distinguishable on its facts",
                 "Court distinguishes habeas-vs-§1983 contexts.", "disagree", "Cited by"),
            auth(85272, "M'Culloch v. Maryland", "17 U.S. 316", "Cited by", "I",
                 "as M'Culloch observed",
                 "Background.", "agree"),
            auth(9200002, "Younger v. Harris", "401 U.S. 37", "Cited by", "II",
                 "noting Younger abstention concerns",
                 "Cf. cite.", "unverified"),
            auth(9200003, "Mitchum v. Foster", "407 U.S. 225", "Cited by", "III",
                 "consistent with Mitchum",
                 "Standard cite.", "unverified"),
        ],
        "cited_by": [
            cb(4729777, "Hernández v. Mesa", "589 U.S. ___", "scotus", "2020-02-25",
               "Cited by", "the principles set forth in Allen v. McCurry",
               "Cross-reference within scoped set.", "agree"),
            cb(622781, "Sanchez ex rel. DR-S. v. United States", "671 F.3d 86", "ca1", "2012-01-04",
               "Distinguished by", "Allen v. McCurry's reasoning is inapposite here",
               "Cross-reference within scoped set.", "agree"),
            cb(9300001, "Migra v. Warren City School District", "465 U.S. 75", "scotus", "1984-02-23",
               "Cited by", "extending Allen v. McCurry to claim preclusion",
               "Standard cite.", "unverified"),
            cb(9300002, "Haring v. Prosise", "462 U.S. 306", "scotus", "1983-06-13",
               "Distinguished by", "we distinguish Allen on the question presented",
               "Court distinguishing.", "disagree", "Cited by"),
            cb(9300003, "United States v. Reed", "843 F.3d 522", "ca5", "2016-12-08",
               "Reversed and remanded by", "the lower court's application of Allen was error",
               "Treatment-of-prior-judgment language.", "agree"),
            cb(9300004, "Smith v. Department of Corrections", "289 F. Supp. 3d 401", "dist", "2018-03-22",
               "Cited by", "as Allen v. McCurry instructs",
               "Standard cite.", "unverified"),
        ],
    },
    {
        "cluster_id": 4729777,
        "case_name": "Hernández v. Mesa",
        "citation": "589 U.S. ___ (2020)",
        "court": "scotus",
        "date_filed": "2020-02-25",
        "document_text": """## I

The question is whether a Bivens remedy should be extended to claims based on a cross-border shooting by a federal agent.

## II

Bivens established that in some circumstances, a damages action may proceed against a federal officer for violations of the Fourth Amendment. See <citedCase data-cluster-id="108375">Bivens v. Six Unknown Named Agents</citedCase>. Subsequent cases such as <citedCase data-cluster-id="110360">Allen v. McCurry</citedCase> have addressed the contours of similar remedies.

## III

We decline to extend Bivens to this new context. The judgment is affirmed.""",
        "authorities": [
            auth(108375, "Bivens v. Six Unknown Named Agents", "403 U.S. 388", "Limited by", "II",
                 "we decline to extend Bivens to this new context",
                 "Court limits Bivens by refusing to extend its remedy.", "agree"),
            auth(110360, "Allen v. McCurry", "449 U.S. 90", "Cited by", "II",
                 "the principles set forth in Allen v. McCurry",
                 "Cross-reference within scoped set.", "agree"),
            auth(9400001, "Ziglar v. Abbasi", "582 U.S. ___", "Cited by", "II",
                 "Abbasi's two-step analysis",
                 "Standard cite.", "agree"),
            auth(9400002, "Carlson v. Green", "446 U.S. 14", "Distinguished by", "II",
                 "Carlson's context differs materially",
                 "Court distinguishing.", "disagree", "Cited by"),
            auth(9400003, "Davis v. Passman", "442 U.S. 228", "Distinguished by", "II",
                 "we distinguish Davis on its facts",
                 "Court distinguishing.", "agree"),
            auth(9400004, "Wilkie v. Robbins", "551 U.S. 537", "Cited by", "II",
                 "as Wilkie observed",
                 "Tangential.", "unverified"),
            auth(108085, "Pike v. Bruce Church, Inc.", "397 U.S. 137", "Cited by", "I",
                 "see also Pike",
                 "Cf. cite.", "unverified"),
            auth(85412, "Gibbons v. Ogden", "22 U.S. 1", "Cited by", "I",
                 "as Gibbons recognized",
                 "Background.", "unverified"),
            auth(9400005, "Lyons v. City of Los Angeles", "461 U.S. 95", "Questioned by", "III",
                 "we question the continuing viability of certain dicta in Lyons",
                 "Court questioning.", "disagree", "Cited by"),
        ],
        "cited_by": [
            cb(9500001, "Egbert v. Boule", "596 U.S. ___", "scotus", "2022-06-08",
               "Cited by", "consistent with Hernández",
               "Standard cite.", "unverified"),
            cb(9500002, "Ahmed v. Department of Homeland Security", "947 F.3d 1145", "ca9", "2020-09-15",
               "Cited by", "as Hernández held",
               "Standard cite.", "unverified"),
            cb(9500003, "Patel v. United States", "812 F. Supp. 3d 211", "dist", "2021-04-30",
               "Distinguished by", "Hernández's cross-border holding is inapposite here",
               "Court distinguishing.", "agree"),
        ],
    },
    {
        "cluster_id": 117927,
        "case_name": "United States v. Lopez",
        "citation": "514 U.S. 549 (1995)",
        "court": "scotus",
        "date_filed": "1995-04-26",
        "document_text": """## I

The Gun-Free School Zones Act of 1990 makes it a federal offense for any individual knowingly to possess a firearm at a place that the individual knows is a school zone. We hold that the Act exceeds the authority of Congress to regulate commerce among the several States.

## II

We have identified three broad categories of activity that Congress may regulate under its commerce power. See <citedCase data-cluster-id="85412">Gibbons v. Ogden</citedCase>. The Act in question falls outside all three.""",
        "authorities": [
            auth(85412, "Gibbons v. Ogden", "22 U.S. 1", "Cited by", "II",
                 "as Gibbons articulated",
                 "Foundational cite.", "agree"),
            auth(9600001, "Wickard v. Filburn", "317 U.S. 111", "Disapproved by", "II",
                 "we have not held that the aggregation principle of Wickard extends to non-economic activity",
                 "Court signaling disapproval of broad reading.", "agree"),
            auth(9600002, "United States v. Darby", "312 U.S. 100", "Distinguished by", "II",
                 "Darby concerned economic activity",
                 "Court distinguishing.", "agree"),
            auth(9600003, "Heart of Atlanta Motel v. United States", "379 U.S. 241", "Distinguished by", "II",
                 "Heart of Atlanta involved interstate channels",
                 "Court distinguishing.", "agree"),
            auth(9600004, "Hodel v. Indiana", "452 U.S. 314", "Cited by", "II",
                 "Hodel acknowledged the limit",
                 "Tangential.", "unverified"),
            auth(9600005, "NLRB v. Jones & Laughlin Steel Corp.", "301 U.S. 1", "Criticized by", "II",
                 "we have observed that Jones & Laughlin's reasoning has been overstated by some lower courts",
                 "Court criticizing readings of the case.", "agree"),
            auth(85272, "M'Culloch v. Maryland", "17 U.S. 316", "Cited by", "II",
                 "see M'Culloch for the foundational analysis",
                 "Background.", "agree"),
            auth(9600006, "Perez v. United States", "402 U.S. 146", "Distinguished by", "II",
                 "Perez involved demonstrably economic activity",
                 "Court distinguishing.", "agree"),
            auth(108085, "Pike v. Bruce Church, Inc.", "397 U.S. 137", "Cited by", "I",
                 "as Pike noted",
                 "Tangential.", "unverified"),
            auth(96276, "Lochner v. New York", "198 U.S. 45", "Cited by", "I",
                 "even before Lochner",
                 "Background.", "unverified"),
            auth(9600007, "Maryland v. Wirtz", "392 U.S. 183", "Distinguished by", "II",
                 "Wirtz's circumstances are not present here",
                 "Court distinguishing.", "disagree", "Cited by"),
            auth(110985, "INS v. Chadha", "462 U.S. 919", "Cited by", "III",
                 "see Chadha",
                 "Cf cite.", "unverified"),
        ],
        "cited_by": [
            cb(9700001, "United States v. Morrison", "529 U.S. 598", "scotus", "2000-05-15",
               "Cited by", "extending the reasoning of Lopez",
               "Companion case.", "agree"),
            cb(9700002, "Gonzales v. Raich", "545 U.S. 1", "Distinguished by", "scotus", "2005-06-06",
               "Distinguished by", "Lopez did not address economic activity in a comprehensive regulatory scheme",
               "Court distinguishing.", "agree"),
            cb(9700003, "United States v. Stewart", "451 F.3d 1071", "ca9", "2006-06-12",
               "Cited by", "applying Lopez", "Standard cite.", "unverified"),
            cb(9700004, "United States v. Patton", "451 F.3d 615", "ca10", "2006-06-26",
               "Cited by", "as Lopez held", "Standard cite.", "unverified"),
            cb(9700005, "Brzonkala v. Va. Polytechnic Institute", "169 F.3d 820", "ca4", "1999-03-05",
               "Cited by", "Lopez controls", "Standard cite.", "agree"),
            cb(9700006, "United States v. Carter", "270 F.3d 731", "ca8", "2001-11-09",
               "Cited by", "Lopez requires a substantial effects analysis", "Standard cite.", "unverified"),
            cb(9700007, "United States v. Doe", "938 F. Supp. 2d 290", "dist", "2013-04-29",
               "Reversed by", "the lower court's reading of Lopez was error",
               "Treatment-of-prior-judgment language.", "disagree", "Distinguished by"),
            cb(9700008, "Smith v. United States", "568 U.S. 106", "scotus", "2013-01-09",
               "Cited by", "consistent with Lopez", "Standard cite.", "unverified"),
        ],
    },
    {
        "cluster_id": 145643,
        "case_name": "Empire Healthchoice Assurance, Inc. v. McVeigh",
        "citation": "547 U.S. 677 (2006)",
        "court": "scotus",
        "date_filed": "2006-06-15",
        "document_text": """## I

The question is whether a federal contractor may sue a beneficiary in federal court to enforce a reimbursement provision of a federal employee health benefits contract.

## II

Federal common law governs only in narrow circumstances. See <citedCase data-cluster-id="84759">Erie Railroad v. Tompkins</citedCase>. The mere presence of a federal contract is insufficient.""",
        "authorities": [
            auth(84759, "Erie Railroad v. Tompkins", "304 U.S. 64", "Cited by", "II",
                 "as Erie instructs", "Foundational cite.", "agree"),
            auth(9800001, "Boyle v. United Technologies Corp.", "487 U.S. 500", "Distinguished by", "II",
                 "Boyle involved uniquely federal interests not present here",
                 "Court distinguishing.", "agree"),
            auth(9800002, "Texas Industries, Inc. v. Radcliff Materials, Inc.", "451 U.S. 630", "Overruled by", "II",
                 "to the extent Texas Industries suggested otherwise, it is overruled",
                 "Court overruling.", "agree"),
            auth(9800003, "Clearfield Trust Co. v. United States", "318 U.S. 363", "Cited by", "II",
                 "Clearfield is the standard reference", "Standard cite.", "agree"),
            auth(9800004, "Bank of America v. Parnell", "352 U.S. 29", "Cited by", "II",
                 "as Parnell makes clear", "Standard cite.", "unverified"),
            auth(9800005, "United States v. Kimbell Foods, Inc.", "440 U.S. 715", "Distinguished by", "II",
                 "Kimbell's three-factor test does not apply here",
                 "Court distinguishing.", "disagree", "Cited by"),
            auth(85412, "Gibbons v. Ogden", "22 U.S. 1", "Cited by", "I",
                 "as Gibbons recognized", "Background.", "unverified"),
            auth(108085, "Pike v. Bruce Church, Inc.", "397 U.S. 137", "Cited by", "I",
                 "see Pike", "Tangential.", "unverified"),
        ],
        "cited_by": [
            cb(9900001, "Carlsbad Technology, Inc. v. HIF Bio, Inc.", "556 U.S. 635", "scotus", "2009-05-04",
               "Cited by", "consistent with Empire Healthchoice", "Standard cite.", "unverified"),
            cb(9900002, "Hartmann v. Prudential Insurance Co.", "9 F.3d 1207", "ca7", "1993-11-03",
               "Cited by", "as Empire instructs", "Standard cite.", "unverified"),
            cb(9900003, "Clark v. Velsicol Chemical Corp.", "944 F. Supp. 2d 215", "dist", "2013-05-08",
               "Reversed by", "Empire forecloses the reasoning below", "Court reversing.", "agree"),
            cb(9900004, "Anderson v. Federal Express Corp.", "682 F.3d 47", "ca2", "2012-06-15",
               "Distinguished by", "Empire's federal-common-law analysis is not implicated here",
               "Court distinguishing.", "agree"),
            cb(9900005, "Smith v. United Healthcare Services", "812 F. Supp. 3d 322", "dist", "2020-09-22",
               "Cited by", "Empire applies", "Standard cite.", "unverified"),
        ],
    },
    {
        "cluster_id": 725046,
        "case_name": "United States v. Felix Garcia",
        "citation": "97 F.3d 425 (2d Cir. 1996)",
        "court": "ca2",
        "date_filed": "1996-09-23",
        "document_text": """## I

Defendant appeals his conviction on conspiracy and wire fraud charges, arguing that the district court erred in admitting certain hearsay evidence.

## II

We have repeatedly held that the co-conspirator exception to the hearsay rule requires a preponderance showing of conspiracy. See <citedCase data-cluster-id="91100001">United States v. Bourjaily</citedCase>.""",
        "authorities": [
            auth(9000001, "United States v. Bourjaily", "483 U.S. 171", "Cited by", "II",
                 "the standard articulated in Bourjaily", "Standard cite.", "agree"),
            auth(9000002, "United States v. Inadi", "475 U.S. 387", "Cited by", "II",
                 "as Inadi held", "Standard cite.", "unverified"),
            auth(9000003, "Crawford v. Washington", "541 U.S. 36", "Cited by", "II",
                 "consistent with Crawford", "Tangential.", "unverified"),
            auth(9000004, "United States v. Trent Shepard", "739 F.2d 994", "Distinguished by", "II",
                 "Shepard's facts are distinguishable", "Court distinguishing.", "disagree", "Cited by"),
            auth(9000005, "Federal Rules of Evidence 801(d)(2)(E)", "FRE 801", "Cited by", "II",
                 "as the Rule provides", "Statutory cite.", "unverified"),
            auth(9000006, "United States v. Field", "39 F.3d 15", "Cited by", "I",
                 "we have applied Field's standard", "Standard cite.", "unverified"),
        ],
        "cited_by": [
            cb(91100001, "United States v. Mitchell", "726 F.3d 1006", "ca2", "2013-08-15",
               "Cited by", "as Felix Garcia held", "Standard cite.", "unverified"),
            cb(91100002, "United States v. Davis", "564 F. Supp. 3d 511", "dist", "2021-10-04",
               "Distinguished by", "Felix Garcia's evidentiary holding is inapposite",
               "Court distinguishing.", "agree"),
        ],
    },
    {
        "cluster_id": 527778,
        "case_name": "In Re Stephen C. Perry",
        "citation": "919 F.2d 962 (1st Cir. 1989)",
        "court": "ca1",
        "date_filed": "1989-12-04",
        "document_text": """## I

This appeal arises from a Chapter 11 bankruptcy proceeding involving the dischargeability of certain trust-fund tax obligations.

## II

The relevant statutory framework is found in 11 U.S.C. § 523. Prior decisions of this court have applied the framework consistently. See <citedCase data-cluster-id="84759">Erie Railroad v. Tompkins</citedCase>.""",
        "authorities": [
            auth(84759, "Erie Railroad v. Tompkins", "304 U.S. 64", "Cited by", "II",
                 "Erie governs the choice-of-law analysis here",
                 "Standard cite.", "unverified"),
            auth(91200001, "Begier v. IRS", "496 U.S. 53", "Disapproved by", "II",
                 "we disapprove of the broad reading of Begier adopted below",
                 "Court disapproving.", "agree"),
            auth(91200002, "Slodov v. United States", "436 U.S. 238", "Cited by", "II",
                 "Slodov articulates the doctrine", "Standard cite.", "agree"),
            auth(91200003, "Federal Rules of Bankruptcy Procedure 7001", "FRBP 7001", "Cited by", "II",
                 "as the Rule provides", "Statutory cite.", "unverified"),
            auth(91200004, "United States v. Sotelo", "436 U.S. 268", "Distinguished by", "II",
                 "Sotelo's procedural posture differs", "Court distinguishing.", "agree"),
            auth(91200005, "Drye v. United States", "528 U.S. 49", "Cited by", "II",
                 "consistent with Drye", "Standard cite.", "unverified"),
            auth(91200006, "United States v. National Bank of Commerce", "472 U.S. 713", "Cited by", "II",
                 "as National Bank held", "Standard cite.", "unverified"),
            auth(91200007, "Abrogated v. Rejected Authority", "100 F.2d 100", "Abrogated by", "III",
                 "to the extent prior precedent suggested otherwise, it is abrogated",
                 "Court abrogating.", "agree"),
            auth(91200008, "Cohen v. de la Cruz", "523 U.S. 213", "Cited by", "III",
                 "Cohen is the leading authority", "Standard cite.", "unverified"),
            auth(91200009, "Grogan v. Garner", "498 U.S. 279", "Cited by", "III",
                 "as Grogan instructs", "Standard cite.", "agree"),
            auth(91200010, "Brown v. Felsen", "442 U.S. 127", "Cited by", "III",
                 "see Brown", "Tangential.", "unverified"),
            auth(91200011, "United States v. Whiting Pools, Inc.", "462 U.S. 198", "Cited by", "II",
                 "Whiting Pools provides the framework", "Standard cite.", "disagree", "Distinguished by"),
        ],
        "cited_by": [
            cb(91300001, "In Re Reorganized Companies", "812 B.R. 211", "dist", "2014-05-19",
               "Cited by", "Perry instructs that...", "Standard cite.", "unverified"),
            cb(91300002, "In Re Smith", "289 B.R. 422", "dist", "2003-02-15",
               "Distinguished by", "Perry's facts are distinguishable", "Court distinguishing.", "agree"),
            cb(91300003, "United States v. Williams", "514 F.3d 124", "ca1", "2008-01-25",
               "Cited by", "Perry remains good law", "Standard cite.", "agree"),
            cb(91300004, "In Re Henderson", "423 B.R. 116", "dist", "2010-03-08",
               "Reversed and remanded by", "Perry forecloses the trustee's argument here",
               "Court reversing.", "agree"),
        ],
    },
    {
        "cluster_id": 201580,
        "case_name": "Narragansett Indian v. State of Rhode Island",
        "citation": "449 F.3d 16 (1st Cir. 2005)",
        "court": "ca1",
        "date_filed": "2005-05-12",
        "document_text": """## I

The Narragansett Indian Tribe seeks declaratory relief regarding the State's authority to enforce its tax laws on tribal lands.

## II

The Indian Gaming Regulatory Act and tribal sovereignty principles inform the analysis. See <citedCase data-cluster-id="91400001">California v. Cabazon Band of Mission Indians</citedCase>.""",
        "authorities": [
            auth(91400001, "California v. Cabazon Band of Mission Indians", "480 U.S. 202", "Cited by", "II",
                 "Cabazon's two-prong analysis", "Foundational cite.", "agree"),
            auth(91400002, "Cherokee Nation v. Georgia", "30 U.S. 1", "Cited by", "I",
                 "as Cherokee Nation held", "Background.", "agree"),
            auth(91400003, "Worcester v. Georgia", "31 U.S. 515", "Cited by", "I",
                 "see Worcester for the foundational analysis", "Background.", "agree"),
            auth(91400004, "Oneida Indian Nation v. County of Oneida", "470 U.S. 226", "Distinguished by", "II",
                 "Oneida involved a different statutory scheme", "Court distinguishing.", "agree"),
            auth(91400005, "Seminole Tribe of Florida v. Florida", "517 U.S. 44", "Cited by", "II",
                 "as Seminole Tribe held", "Standard cite.", "agree"),
            auth(91400006, "United States v. Lara", "541 U.S. 193", "Cited by", "II",
                 "Lara reaffirms the principle", "Standard cite.", "unverified"),
            auth(91400007, "Montana v. United States", "450 U.S. 544", "Distinguished by", "II",
                 "Montana's reasoning does not control", "Court distinguishing.", "disagree", "Cited by"),
            auth(91400008, "Strate v. A-1 Contractors", "520 U.S. 438", "Cited by", "II",
                 "Strate is on point", "Standard cite.", "unverified"),
            auth(91400009, "Atkinson Trading Co. v. Shirley", "532 U.S. 645", "Vacated and remanded by", "III",
                 "the trial court's reading of Atkinson cannot stand",
                 "Court vacating prior reasoning.", "agree"),
            auth(91400010, "United States v. Wheeler", "435 U.S. 313", "Cited by", "II",
                 "as Wheeler observed", "Standard cite.", "unverified"),
        ],
        "cited_by": [
            cb(91500001, "Mashantucket Pequot Tribe v. Connecticut", "913 F.3d 167", "ca2", "2019-01-22",
               "Cited by", "Narragansett Indian instructs", "Standard cite.", "unverified"),
            cb(91500002, "Tribe v. State of Maine", "677 F. Supp. 2d 211", "dist", "2010-04-30",
               "Distinguished by", "Narragansett's analysis does not extend here",
               "Court distinguishing.", "agree"),
            cb(91500003, "United States v. Doe", "812 F.3d 911", "ca1", "2016-02-15",
               "Cited by", "consistent with Narragansett", "Standard cite.", "unverified"),
        ],
    },
    {
        "cluster_id": 622781,
        "case_name": "Sanchez ex rel. DR-S. v. United States",
        "citation": "671 F.3d 86 (1st Cir. 2012)",
        "court": "ca1",
        "date_filed": "2012-01-04",
        "document_text": """## I

Plaintiff brings a Federal Tort Claims Act suit alleging negligent supervision by federal officials.

## II

The discretionary function exception to the FTCA bars suits based on agency policy choices. See <citedCase data-cluster-id="91600001">United States v. Gaubert</citedCase>. Issue preclusion as articulated in <citedCase data-cluster-id="110360">Allen v. McCurry</citedCase> is inapposite here.""",
        "authorities": [
            auth(91600001, "United States v. Gaubert", "499 U.S. 315", "Cited by", "II",
                 "Gaubert's two-step analysis governs", "Foundational cite.", "agree"),
            auth(110360, "Allen v. McCurry", "449 U.S. 90", "Distinguished by", "II",
                 "Allen v. McCurry's reasoning is inapposite here",
                 "Cross-reference within scoped set.", "agree"),
            auth(91600002, "Berkovitz v. United States", "486 U.S. 531", "Cited by", "II",
                 "Berkovitz's two-step framework", "Standard cite.", "unverified"),
            auth(91600003, "Indian Towing Co. v. United States", "350 U.S. 61", "Cited by", "II",
                 "as Indian Towing held", "Standard cite.", "unverified"),
            auth(91600004, "United States v. S.A. Empresa de Viacao Aerea Rio Grandense", "467 U.S. 797", "Cited by", "II",
                 "Varig Airlines confirms", "Standard cite.", "unverified"),
            auth(91600005, "Dalehite v. United States", "346 U.S. 15", "Distinguished by", "II",
                 "Dalehite's facts are distinguishable", "Court distinguishing.", "agree"),
            auth(91600006, "Federal Tort Claims Act § 2680(a)", "28 U.S.C. § 2680(a)", "Cited by", "II",
                 "as the statute provides", "Statutory cite.", "unverified"),
            auth(91600007, "Bivens v. Six Unknown Named Agents", "403 U.S. 388", "Cited by", "II",
                 "see Bivens for the alternative remedy", "Tangential.", "unverified"),
            auth(91600008, "Westfall v. Erwin", "484 U.S. 292", "Cited by", "I",
                 "as Westfall recognized", "Background.", "unverified"),
        ],
        "cited_by": [
            cb(91700001, "Lopez-Garcia v. United States", "923 F.3d 144", "ca1", "2019-04-15",
               "Cited by", "Sanchez instructs", "Standard cite.", "unverified"),
            cb(91700002, "Doe v. United States", "452 F. Supp. 3d 89", "dist", "2020-04-08",
               "Cited by", "as Sanchez held", "Standard cite.", "unverified"),
        ],
    },
    {
        "cluster_id": 1254,
        "case_name": "Chamberlin v. Town of Stoughton",
        "citation": "601 F.3d 25 (1st Cir. 2010)",
        "court": "ca1",
        "date_filed": "2010-04-01",
        "document_text": """## I

Plaintiff brings a § 1983 claim alleging First Amendment retaliation by municipal officials following her public criticism of town policy.

## II

The standard for First Amendment retaliation requires a showing that protected speech was a substantial factor in the adverse action. See <citedCase data-cluster-id="91800001">Mt. Healthy City School District v. Doyle</citedCase>.""",
        "authorities": [
            auth(91800001, "Mt. Healthy City School District v. Doyle", "429 U.S. 274", "Cited by", "II",
                 "the Mt. Healthy framework", "Foundational cite.", "agree"),
            auth(91800002, "Pickering v. Board of Education", "391 U.S. 563", "Cited by", "II",
                 "Pickering's balancing test", "Standard cite.", "agree"),
            auth(91800003, "Garcetti v. Ceballos", "547 U.S. 410", "Cited by", "II",
                 "as Garcetti instructs", "Standard cite.", "unverified"),
            auth(91800004, "Connick v. Myers", "461 U.S. 138", "Cited by", "II",
                 "Connick's matter-of-public-concern analysis", "Standard cite.", "agree"),
            auth(91800005, "Hartman v. Moore", "547 U.S. 250", "Distinguished by", "II",
                 "Hartman concerned retaliatory prosecution, not at issue here",
                 "Court distinguishing.", "disagree", "Cited by"),
            auth(91800006, "Crawford-El v. Britton", "523 U.S. 574", "Cited by", "I",
                 "as Crawford-El held", "Tangential.", "unverified"),
            auth(91800007, "Saucier v. Katz", "533 U.S. 194", "Cited by", "II",
                 "the qualified immunity analysis under Saucier", "Standard cite.", "unverified"),
            auth(91800008, "Pearson v. Callahan", "555 U.S. 223", "Cited by", "II",
                 "as Pearson clarified", "Standard cite.", "unverified"),
        ],
        "cited_by": [
            cb(91900001, "Smith v. Town of Hudson", "812 F.3d 144", "ca1", "2016-02-09",
               "Cited by", "Chamberlin's reasoning controls", "Standard cite.", "unverified"),
            cb(91900002, "Doe v. City of Boston", "452 F. Supp. 3d 401", "dist", "2020-04-15",
               "Distinguished by", "Chamberlin's facts are distinguishable",
               "Court distinguishing.", "agree"),
            cb(91900003, "Brown v. Town of Brookline", "923 F.3d 211", "ca1", "2019-05-22",
               "Cited by", "consistent with Chamberlin", "Standard cite.", "unverified"),
        ],
    },
]


def get_court_display(court_id: str) -> str:
    """Return human-readable court name."""
    return COURT_DISPLAY.get(court_id, court_id)
