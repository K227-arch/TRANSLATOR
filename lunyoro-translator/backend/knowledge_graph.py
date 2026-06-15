"""
knowledge_graph.py
==================
Linguistic Knowledge Graph for Runyoro-Rutooro.

Models the grammar as a directed graph where:
  - Nodes = linguistic entities (noun classes, words, rules, tenses, affixes)
  - Edges = relationships (HAS_PREFIX, PLURAL_OF, AGREES_WITH, DERIVES_FROM,
             TAKES_TENSE, APPLIES_RULE, EXAMPLE_OF, RELATED_TO)

Enables:
  - Explainable AI translation (why was this word chosen?)
  - Grammar tutoring (what rule applies here?)
  - Intelligent correction (what is the correct form?)
  - Educational reasoning (how does this word relate to others?)

Uses a pure-Python in-memory graph (no external DB required).
Optionally exports to JSON for persistence or frontend consumption.

Usage:
    from knowledge_graph import LinguisticKG
    kg = LinguisticKG()
    kg.build()

    # Query
    result = kg.explain_word("omulimi")
    result = kg.get_noun_class_info(1)
    result = kg.find_related(word="okulima", rel="DERIVES_FROM")
    result = kg.grammar_path("okulima", "omulimi")
    result = kg.correct_form("omulimi", "plural")
    result = kg.tutor_question("What is the plural of omulimi?")
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent


# ── Graph primitives ──────────────────────────────────────────────────────────

class Node:
    __slots__ = ("id", "type", "label", "props")

    def __init__(self, node_id: str, node_type: str, label: str, **props):
        self.id    = node_id
        self.type  = node_type
        self.label = label
        self.props = props

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type,
                "label": self.label, **self.props}


class Edge:
    __slots__ = ("src", "rel", "tgt", "props")

    def __init__(self, src: str, rel: str, tgt: str, **props):
        self.src   = src
        self.rel   = rel
        self.tgt   = tgt
        self.props = props

    def to_dict(self) -> dict:
        return {"src": self.src, "rel": self.rel,
                "tgt": self.tgt, **self.props}


class LinguisticKG:
    """In-memory Linguistic Knowledge Graph for Runyoro-Rutooro."""

    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        # Adjacency: src_id -> list of Edge
        self._out: dict[str, list[Edge]] = {}
        # Reverse: tgt_id -> list of Edge
        self._in:  dict[str, list[Edge]] = {}
        self._built = False

    # ── Graph construction helpers ────────────────────────────────────────────

    def _add_node(self, node_id: str, node_type: str, label: str, **props) -> Node:
        if node_id not in self._nodes:
            n = Node(node_id, node_type, label, **props)
            self._nodes[node_id] = n
            self._out[node_id] = []
            self._in[node_id]  = []
        return self._nodes[node_id]

    def _add_edge(self, src: str, rel: str, tgt: str, **props):
        e = Edge(src, rel, tgt, **props)
        self._edges.append(e)
        self._out.setdefault(src, []).append(e)
        self._in.setdefault(tgt,  []).append(e)

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> "LinguisticKG":
        """Populate the graph from language_rules data."""
        if self._built:
            return self
        self._build_noun_classes()
        self._build_tense_system()
        self._build_verb_derivatives()
        self._build_concordial_agreement()
        self._build_word_examples()
        self._build_grammar_rules()
        self._build_kinship_terms()
        self._build_colour_names()
        self._build_numbers()
        self._built = True
        return self

    def _build_noun_classes(self):
        from language_rules import NOUN_CLASSES, PLURAL_SOUND_CHANGES
        # Root node
        self._add_node("noun_class_system", "SYSTEM", "Runyoro-Rutooro Noun Class System",
                        description="15 noun classes governing prefix, plural, and concordial agreement")

        CLASS_DESCS = {
            1:  "persons (singular) — omu-/omw-",
            2:  "persons (plural) — aba-/ab-",
            3:  "trees/plants (singular) — omu-/omw-",
            4:  "trees/plants (plural) — emi-/emy-",
            5:  "augmentatives, body parts (singular) — eri-/ery-",
            6:  "plural of class 5; mass nouns — ama-/ame-/amo-",
            7:  "things, abstracts (singular) — eki-/eky-",
            8:  "things, abstracts (plural) — ebi-/eby-",
            9:  "animals, foreign words (singular) — en-/em-",
            10: "animals, foreign words (plural) — en-/em-",
            11: "long/thin objects, languages (singular) — oru-/orw-",
            12: "diminutives (singular) — aka-/akw-",
            13: "diminutives (plural) — utu-/utw-",
            14: "abstract/mass nouns — obu-/obw-",
            15: "verbal infinitives, body parts — oku-/okw-",
        }
        PREFIXES = {
            1: "omu", 2: "aba", 3: "omu", 4: "emi", 5: "eri", 6: "ama",
            7: "eki", 8: "ebi", 9: "en",  10: "en", 11: "oru", 12: "aka",
            13: "utu", 14: "obu", 15: "oku",
        }
        PLURAL_MAP = {1:2, 2:1, 3:4, 4:3, 5:6, 7:8, 8:7, 9:10, 10:9,
                      11:10, 12:13, 13:12, 14:6, 15:6}

        for cl_num, desc in CLASS_DESCS.items():
            nid = f"nc_{cl_num}"
            self._add_node(nid, "NOUN_CLASS", f"Class {cl_num}",
                           class_number=cl_num,
                           description=desc,
                           prefix=PREFIXES.get(cl_num, ""),
                           sg_or_pl="singular" if cl_num in (1,3,5,7,9,11,12,14,15) else "plural")
            self._add_edge("noun_class_system", "CONTAINS", nid)

        # Plural relationships
        for sg, pl in PLURAL_MAP.items():
            self._add_edge(f"nc_{sg}", "PLURAL_IS", f"nc_{pl}",
                           description=f"Class {sg} nouns form plural in Class {pl}")

        # Irregular class-11 plurals
        for singular, plural in PLURAL_SOUND_CHANGES.items():
            sid = f"word_{singular}"
            pid = f"word_{plural}"
            self._add_node(sid, "WORD", singular, pos="noun", noun_class=11)
            self._add_node(pid, "WORD", plural,   pos="noun", noun_class=10)
            self._add_edge(sid, "PLURAL_OF",   pid, rule="class11_irregular")
            self._add_edge(sid, "BELONGS_TO",  "nc_11")
            self._add_edge(pid, "BELONGS_TO",  "nc_10")
            self._add_edge(sid, "IRREGULAR_PLURAL", pid,
                           note="vowel mutation in plural formation")

    def _build_tense_system(self):
        from language_rules import TENSES, TENSE_MARKERS, SUBJECT_PREFIXES
        self._add_node("tense_system", "SYSTEM", "Runyoro-Rutooro Tense System")

        for tense_name, info in TENSES.items():
            tid = f"tense_{tense_name}"
            self._add_node(tid, "TENSE", tense_name,
                           marker=info.get("marker", ""),
                           example=info.get("example", ""),
                           meaning=info.get("meaning", ""))
            self._add_edge("tense_system", "CONTAINS", tid)

        # Tense marker nodes
        for marker_name, marker_val in TENSE_MARKERS.items():
            mid = f"marker_{marker_name}"
            self._add_node(mid, "AFFIX", marker_val,
                           affix_type="tense_marker",
                           tense=marker_name)
            # Link to tense node if exists
            tid = f"tense_{marker_name}"
            if tid in self._nodes:
                self._add_edge(tid, "USES_MARKER", mid)

        # Subject prefix nodes
        for person, prefix in SUBJECT_PREFIXES.items():
            pid = f"subj_{person}"
            self._add_node(pid, "AFFIX", prefix,
                           affix_type="subject_prefix",
                           person=person)
            self._add_edge("tense_system", "HAS_SUBJECT_PREFIX", pid)

        # Tense relationships
        TENSE_RELATIONS = [
            ("tense_present_imperfect", "NEGATED_BY", "tense_negative_present",
             "ti- prefix negates present imperfect"),
            ("tense_present_perfect",   "NEGATED_BY", "tense_negative_perfect",
             "tinka- prefix negates present perfect"),
            ("tense_recent_past",       "PRECEDES",   "tense_remote_past",
             "recent past is closer in time"),
            ("tense_future_immediate",  "PRECEDES",   "tense_future_remote",
             "immediate future is sooner"),
        ]
        for src, rel, tgt, note in TENSE_RELATIONS:
            if src in self._nodes and tgt in self._nodes:
                self._add_edge(src, rel, tgt, note=note)

    def _build_verb_derivatives(self):
        from language_rules import DERIVATIVE_SUFFIXES, VERB_NOUN_EXAMPLES
        self._add_node("verb_derivation", "SYSTEM", "Verb Derivation System",
                        description="Suffixes that derive new verb meanings from a root")

        DERIV_DESCS = {
            "causative":   "cause the action to happen (-isa/-esa/-ya)",
            "passive":     "subject receives the action (-ibwa/-ebwa/-wa)",
            "reciprocal":  "action done to each other (-ana/-ngana)",
            "reversive":   "undo or reverse the action (-ura/-ora)",
            "neuter":      "possibility/state after action (-ika/-eka)",
            "intensive":   "thorough/complete action (-rra/-rruka)",
            "applied":     "action done for/at/with reference to (-era/-ira)",
            "positional":  "be in a position (-ama)",
        }
        for deriv_type, suffixes in DERIVATIVE_SUFFIXES.items():
            did = f"deriv_{deriv_type}"
            self._add_node(did, "DERIVATION", deriv_type,
                           suffixes=suffixes,
                           description=DERIV_DESCS.get(deriv_type, ""))
            self._add_edge("verb_derivation", "CONTAINS", did)

        # Verb-to-noun derivation examples
        for infinitive, forms in VERB_NOUN_EXAMPLES.items():
            vid = f"word_{infinitive}"
            self._add_node(vid, "WORD", infinitive, pos="verb_infinitive")
            self._add_edge(vid, "BELONGS_TO", "nc_15",
                           note="infinitives belong to class 15 (oku-)")
            for form_type, derived_word in forms.items():
                dwid = f"word_{derived_word}"
                self._add_node(dwid, "WORD", derived_word,
                               pos="noun", derived_from=infinitive,
                               derivation_type=form_type)
                self._add_edge(vid,  "DERIVES_TO",   dwid, via=form_type)
                self._add_edge(dwid, "DERIVES_FROM", vid,  via=form_type)
                # Link to noun class
                if form_type == "agent":
                    self._add_edge(dwid, "BELONGS_TO", "nc_1")
                elif form_type == "action":
                    self._add_edge(dwid, "BELONGS_TO", "nc_3")
                elif form_type == "method":
                    self._add_edge(dwid, "BELONGS_TO", "nc_9")

    def _build_concordial_agreement(self):
        from language_rules import CONCORDIAL_AGREEMENT, NUMERAL_CONCORDS
        self._add_node("agreement_system", "SYSTEM", "Concordial Agreement System",
                        description="Every noun class has subject, object, adjective, and demonstrative concords")

        for cl_num, (subj, obj, adj, dem) in CONCORDIAL_AGREEMENT.items():
            nid = f"nc_{cl_num}"
            if nid not in self._nodes:
                self._add_node(nid, "NOUN_CLASS", f"Class {cl_num}", class_number=cl_num)

            # Subject concord
            scid = f"concord_subj_{cl_num}"
            self._add_node(scid, "CONCORD", subj.strip("-"),
                           concord_type="subject", noun_class=cl_num,
                           description=f"Class {cl_num} subject concord: {subj}")
            self._add_edge(nid, "HAS_SUBJECT_CONCORD", scid)

            # Object concord
            ocid = f"concord_obj_{cl_num}"
            self._add_node(ocid, "CONCORD", obj.strip("-"),
                           concord_type="object", noun_class=cl_num,
                           description=f"Class {cl_num} object concord: {obj}")
            self._add_edge(nid, "HAS_OBJECT_CONCORD", ocid)

            # Adjective concord
            acid = f"concord_adj_{cl_num}"
            self._add_node(acid, "CONCORD", adj.strip("-"),
                           concord_type="adjective", noun_class=cl_num,
                           description=f"Class {cl_num} adjective concord: {adj}")
            self._add_edge(nid, "HAS_ADJ_CONCORD", acid)

            # Demonstrative
            demid = f"dem_{cl_num}"
            self._add_node(demid, "DEMONSTRATIVE", dem,
                           noun_class=cl_num,
                           description=f"Class {cl_num} demonstrative: {dem}")
            self._add_edge(nid, "HAS_DEMONSTRATIVE", demid)

            self._add_edge("agreement_system", "GOVERNS", nid)

        # Numeral concords
        for cl_num, concord in NUMERAL_CONCORDS.items():
            nid = f"nc_{cl_num}"
            ncid = f"concord_num_{cl_num}"
            self._add_node(ncid, "CONCORD", concord,
                           concord_type="numeral", noun_class=cl_num,
                           description=f"Class {cl_num} numeral concord (numbers 1-5): {concord}")
            if nid in self._nodes:
                self._add_edge(nid, "HAS_NUMERAL_CONCORD", ncid)

    def _build_grammar_rules(self):
        from language_rules import (
            NASAL_ASSIMILATION, NI_PREFIX_CHANGE,
            CONSONANT_SUFFIX_CHANGES, RL_RULE
        )
        self._add_node("orthography_rules", "SYSTEM", "Orthographic Rules",
                        description="Sound change and spelling rules for Runyoro-Rutooro")

        # R/L rule
        self._add_node("rule_rl", "RULE", "R/L Rule",
                        description=RL_RULE,
                        applies_to="all words",
                        example="L only before/after e or i; R elsewhere")
        self._add_edge("orthography_rules", "CONTAINS", "rule_rl")

        # Nasal assimilation
        for src_cluster, tgt_cluster in NASAL_ASSIMILATION.items():
            rid = f"rule_nasal_{src_cluster}"
            self._add_node(rid, "RULE", f"Nasal: {src_cluster} -> {tgt_cluster}",
                           rule_type="nasal_assimilation",
                           input_cluster=src_cluster,
                           output_cluster=tgt_cluster,
                           description=f"Nasal assimilation: {src_cluster} becomes {tgt_cluster}")
            self._add_edge("orthography_rules", "CONTAINS", rid)

        # ni- prefix change
        for src, tgt in NI_PREFIX_CHANGE.items():
            rid = f"rule_ni_{src}"
            self._add_node(rid, "RULE", f"ni-change: {src} -> {tgt}",
                           rule_type="ni_prefix_change",
                           input_form=src, output_form=tgt,
                           description=f"Present imperfect: {src} -> {tgt} before u-class concords")
            self._add_edge("orthography_rules", "CONTAINS", rid)

        # Consonant suffix mutations
        for (cons, suffix), result in CONSONANT_SUFFIX_CHANGES.items():
            rid = f"rule_cons_{cons}_{suffix.strip('-')}"
            self._add_node(rid, "RULE", f"{cons}+{suffix} -> {result}",
                           rule_type="consonant_suffix_mutation",
                           consonant=cons, suffix=suffix, result=result,
                           description=f"Stem ending in {cons!r} + {suffix} -> {result}")
            self._add_edge("orthography_rules", "CONTAINS", rid)

    def _build_word_examples(self):
        """Add representative vocabulary with full class + derivation links."""
        VOCAB = [
            # (word, english, pos, noun_class)
            ("omuntu",   "person",       "noun", 1),
            ("abantu",   "people",       "noun", 2),
            ("omuti",    "tree",         "noun", 3),
            ("emiti",    "trees",        "noun", 4),
            ("ente",     "cow",          "noun", 9),
            ("ente",     "cows",         "noun", 10),
            ("enju",     "house",        "noun", 9),
            ("amaju",    "houses",       "noun", 6),
            ("ekitabu",  "book",         "noun", 7),
            ("ebitabu",  "books",        "noun", 8),
            ("orugoye",  "cloth",        "noun", 11),
            ("engoye",   "cloths",       "noun", 10),
            ("akajuma",  "grain/pill",   "noun", 12),
            ("obujuma",  "grains",       "noun", 14),
            ("okulima",  "to cultivate", "verb", 15),
            ("okugenda", "to go/walk",   "verb", 15),
            ("okusoma",  "to read",      "verb", 15),
            ("okulya",   "to eat",       "verb", 15),
            ("omulimi",  "cultivator",   "noun", 1),
            ("omulimo",  "work",         "noun", 3),
            ("omuzaani", "player",       "noun", 1),
            ("omuzaano", "play/game",    "noun", 3),
            ("omubazi",  "carpenter",    "noun", 1),
            ("omubaro",  "counting",     "noun", 3),
        ]
        for word, english, pos, nc in VOCAB:
            wid = f"word_{word}"
            if wid not in self._nodes:
                self._add_node(wid, "WORD", word,
                               english=english, pos=pos, noun_class=nc)
            nid = f"nc_{nc}"
            if nid in self._nodes:
                self._add_edge(wid, "BELONGS_TO", nid)

        # Explicit plural pairs
        PLURAL_PAIRS = [
            ("omuntu", "abantu", 1, 2),
            ("omuti",  "emiti",  3, 4),
            ("ekitabu","ebitabu",7, 8),
            ("orugoye","engoye", 11, 10),
            ("akajuma","obujuma",12, 14),
        ]
        for sg, pl, sg_cl, pl_cl in PLURAL_PAIRS:
            sid, pid = f"word_{sg}", f"word_{pl}"
            if sid in self._nodes and pid in self._nodes:
                self._add_edge(sid, "PLURAL_IS",   pid, rule=f"class{sg_cl}_to_{pl_cl}")
                self._add_edge(pid, "SINGULAR_IS", sid, rule=f"class{pl_cl}_from_{sg_cl}")

    def _build_kinship_terms(self):
        from language_rules_gr4 import KINSHIP_TERMS
        self._add_node("kinship_system", "SYSTEM", "Kinship Terms",
                        description="Runyoro-Rutooro names of relationship with possessive agreement")
        for relation, persons in KINSHIP_TERMS.items():
            rid = f"kinship_{relation}"
            self._add_node(rid, "KINSHIP", relation,
                           relation_type=relation,
                           forms=persons)
            self._add_edge("kinship_system", "CONTAINS", rid)
            for person, form in persons.items():
                fid = f"kinship_{relation}_{person}"
                self._add_node(fid, "WORD", form,
                               kinship_relation=relation,
                               person=person,
                               english=f"{person} {relation}")
                self._add_edge(rid, "HAS_FORM", fid, person=person)

    def _build_colour_names(self):
        from language_rules_gr5 import CLASS_9A_EXAMPLES
        self._add_node("colour_system", "SYSTEM", "Colour Names (Class 9a)",
                        description="Runyoro-Rutooro colour names — Class 9a (no prefix)")
        COLOURS = {k: v for k, v in CLASS_9A_EXAMPLES.items()
                   if any(c in v.lower() for c in
                          ["green","white","black","brown","yellow","grey","blue","red","purple"])}
        for runyoro, english in COLOURS.items():
            cid = f"colour_{runyoro}"
            self._add_node(cid, "COLOUR", runyoro,
                           english=english, noun_class="9a",
                           description=f"{runyoro} = {english}")
            self._add_edge("colour_system", "CONTAINS", cid)
            self._add_edge(cid, "BELONGS_TO", "nc_9")

    def _build_numbers(self):
        from language_rules import NUMBERS
        self._add_node("number_system", "SYSTEM", "Cardinal Numbers",
                        description="Runyoro-Rutooro cardinal numbers 1-1,000,000")
        for n, word in list(NUMBERS.items())[:20]:
            nid = f"number_{n}"
            self._add_node(nid, "NUMBER", word,
                           value=n, english=str(n),
                           note="numbers 1-5 take numeral concords per noun class")
            self._add_edge("number_system", "CONTAINS", nid)
            if n > 1:
                prev = f"number_{n-1}"
                if prev in self._nodes:
                    self._add_edge(f"number_{n-1}", "PRECEDES", nid)

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> dict | None:
        n = self._nodes.get(node_id)
        return n.to_dict() if n else None

    def find_nodes(self, node_type: str | None = None,
                   label_contains: str | None = None) -> list[dict]:
        results = []
        for n in self._nodes.values():
            if node_type and n.type != node_type:
                continue
            if label_contains and label_contains.lower() not in n.label.lower():
                continue
            results.append(n.to_dict())
        return results

    def find_related(self, word: str, rel: str | None = None,
                     direction: str = "out") -> list[dict]:
        """
        Find nodes related to a word.
        direction: 'out' (edges from word), 'in' (edges to word), 'both'
        """
        wid = f"word_{word}"
        if wid not in self._nodes:
            # Try partial match
            matches = [k for k in self._nodes if word.lower() in k.lower()]
            if not matches:
                return []
            wid = matches[0]

        results = []
        edges = []
        if direction in ("out", "both"):
            edges += self._out.get(wid, [])
        if direction in ("in", "both"):
            edges += self._in.get(wid, [])

        for e in edges:
            if rel and e.rel != rel:
                continue
            other_id = e.tgt if e.src == wid else e.src
            other = self._nodes.get(other_id)
            if other:
                results.append({
                    "relation": e.rel,
                    "direction": "out" if e.src == wid else "in",
                    "node": other.to_dict(),
                    **e.props,
                })
        return results

    def get_noun_class_info(self, class_num: int | str) -> dict:
        """Return full info about a noun class including concords and examples."""
        nid = f"nc_{class_num}"
        node = self._nodes.get(nid)
        if not node:
            return {"error": f"Noun class {class_num} not found"}

        result = node.to_dict()
        result["concords"] = {}
        result["examples"] = []
        result["plural_class"] = None

        for e in self._out.get(nid, []):
            tgt = self._nodes.get(e.tgt)
            if not tgt:
                continue
            if e.rel == "HAS_SUBJECT_CONCORD":
                result["concords"]["subject"] = tgt.label
            elif e.rel == "HAS_OBJECT_CONCORD":
                result["concords"]["object"] = tgt.label
            elif e.rel == "HAS_ADJ_CONCORD":
                result["concords"]["adjective"] = tgt.label
            elif e.rel == "HAS_DEMONSTRATIVE":
                result["concords"]["demonstrative"] = tgt.label
            elif e.rel == "HAS_NUMERAL_CONCORD":
                result["concords"]["numeral"] = tgt.label
            elif e.rel == "PLURAL_IS":
                result["plural_class"] = tgt.to_dict()

        # Words belonging to this class
        for e in self._in.get(nid, []):
            if e.rel == "BELONGS_TO":
                w = self._nodes.get(e.src)
                if w and w.type == "WORD":
                    result["examples"].append(w.to_dict())

        return result

    def explain_word(self, word: str) -> dict:
        """
        Explain a word: its noun class, derivation, related forms, grammar rules.
        This is the core explainable AI function.
        """
        wid = f"word_{word}"
        node = self._nodes.get(wid)
        if not node:
            return {"word": word, "found": False,
                    "message": f"'{word}' not in knowledge graph. "
                               f"Try find_related() or get_noun_class_info()."}

        result = {
            "word": word,
            "found": True,
            "type": node.type,
            "properties": node.props,
            "noun_class": None,
            "derivations": [],
            "plural": None,
            "singular": None,
            "grammar_rules": [],
            "related_words": [],
        }

        for e in self._out.get(wid, []):
            tgt = self._nodes.get(e.tgt)
            if not tgt:
                continue
            if e.rel == "BELONGS_TO" and tgt.type == "NOUN_CLASS":
                result["noun_class"] = tgt.to_dict()
            elif e.rel == "DERIVES_TO":
                result["derivations"].append({
                    "via": e.props.get("via", ""),
                    "word": tgt.to_dict()
                })
            elif e.rel == "PLURAL_IS":
                result["plural"] = tgt.to_dict()
            elif e.rel == "DERIVES_FROM":
                result["related_words"].append({
                    "relation": "derived_from",
                    "word": tgt.to_dict()
                })

        for e in self._in.get(wid, []):
            src = self._nodes.get(e.src)
            if not src:
                continue
            if e.rel == "PLURAL_IS":
                result["singular"] = src.to_dict()
            elif e.rel == "DERIVES_TO":
                result["related_words"].append({
                    "relation": f"source_of_{e.props.get('via','')}",
                    "word": src.to_dict()
                })

        # Infer applicable grammar rules from prefix
        w_lower = word.lower()
        if w_lower.startswith(("nb", "np", "nr", "nl")):
            result["grammar_rules"].append("Nasal assimilation applies")
        if any(w_lower.startswith(p) for p in ("ni", "numu", "nugu")):
            result["grammar_rules"].append("ni->nu prefix change may apply")
        if re.search(r'[rtj](ire|ere|i|ya)$', w_lower):
            result["grammar_rules"].append("Consonant+suffix mutation applies")

        return result

    def correct_form(self, word: str, target: str) -> dict:
        """
        Suggest the correct grammatical form of a word.
        target: 'plural', 'singular', 'agent_noun', 'action_noun', 'causative', etc.
        """
        wid = f"word_{word}"
        if wid not in self._nodes:
            return {"word": word, "target": target, "result": None,
                    "message": f"'{word}' not in knowledge graph"}

        rel_map = {
            "plural":      ("PLURAL_IS",   "out"),
            "singular":    ("PLURAL_IS",   "in"),
            "agent_noun":  ("DERIVES_TO",  "out"),
            "action_noun": ("DERIVES_TO",  "out"),
            "source_verb": ("DERIVES_FROM","out"),
        }
        rel, direction = rel_map.get(target, (None, None))
        if not rel:
            return {"word": word, "target": target, "result": None,
                    "message": f"Unknown target form '{target}'"}

        edges = self._out.get(wid, []) if direction == "out" else self._in.get(wid, [])
        for e in edges:
            if e.rel == rel:
                if target in ("agent_noun", "action_noun"):
                    if e.props.get("via", "") != target.replace("_noun", ""):
                        continue
                other_id = e.tgt if direction == "out" else e.src
                other = self._nodes.get(other_id)
                if other:
                    return {"word": word, "target": target,
                            "result": other.label,
                            "explanation": e.props}
        return {"word": word, "target": target, "result": None,
                "message": f"No {target} form found for '{word}' in graph"}

    def grammar_path(self, word_a: str, word_b: str) -> dict:
        """
        Find the grammatical relationship path between two words.
        Uses BFS over the graph.
        """
        start = f"word_{word_a}"
        end   = f"word_{word_b}"
        if start not in self._nodes:
            return {"found": False, "message": f"'{word_a}' not in graph"}
        if end not in self._nodes:
            return {"found": False, "message": f"'{word_b}' not in graph"}

        # BFS
        from collections import deque
        queue = deque([(start, [])])
        visited = {start}
        while queue:
            current, path = queue.popleft()
            if current == end:
                return {"found": True, "path": path,
                        "length": len(path),
                        "explanation": self._explain_path(path)}
            for e in self._out.get(current, []) + self._in.get(current, []):
                nxt = e.tgt if e.src == current else e.src
                if nxt not in visited:
                    visited.add(nxt)
                    step = {"from": current, "rel": e.rel, "to": nxt}
                    queue.append((nxt, path + [step]))
            if len(visited) > 500:  # safety limit
                break
        return {"found": False, "message": f"No path found between '{word_a}' and '{word_b}'"}

    def _explain_path(self, path: list) -> str:
        if not path:
            return "Same word"
        parts = []
        for step in path:
            src = step["from"].replace("word_", "").replace("nc_", "Class ")
            tgt = step["to"].replace("word_", "").replace("nc_", "Class ")
            parts.append(f"{src} --[{step['rel']}]--> {tgt}")
        return " | ".join(parts)

    def tutor_question(self, question: str) -> dict:
        """
        Answer a grammar tutoring question using the knowledge graph.
        Supports: plural, singular, class, derivation, concord queries.
        """
        q = question.lower().strip()

        # "What is the plural of X?"
        m = re.search(r'plural of (\w+)', q)
        if m:
            word = m.group(1)
            result = self.correct_form(word, "plural")
            if result.get("result"):
                nc = self.explain_word(word).get("noun_class", {})
                pl_class = nc.get("plural_class", {}) if nc else {}
                return {
                    "question": question,
                    "answer": result["result"],
                    "explanation": (
                        f"'{word}' belongs to {nc.get('label','?')} "
                        f"({nc.get('description','')}).\n"
                        f"Its plural is '{result['result']}' "
                        f"in {pl_class.get('label','?') if pl_class else '?'}."
                    ),
                }
            return {"question": question, "answer": None,
                    "explanation": f"Plural of '{word}' not found in knowledge graph."}

        # "What class is X?"
        m = re.search(r'class (?:is )?(\w+)|(\w+) (?:is in |belongs to )?class', q)
        if m:
            word = m.group(1) or m.group(2)
            info = self.explain_word(word)
            nc = info.get("noun_class")
            if nc:
                return {"question": question,
                        "answer": nc.get("label"),
                        "explanation": nc.get("description", "")}

        # "What is the agent noun of X?"
        m = re.search(r'agent noun of (\w+)', q)
        if m:
            result = self.correct_form(m.group(1), "agent_noun")
            return {"question": question, "answer": result.get("result"),
                    "explanation": f"Agent noun (one who does the action) of '{m.group(1)}'"}

        # "What does X mean?"
        m = re.search(r'(?:what does|meaning of) (\w+)', q)
        if m:
            info = self.explain_word(m.group(1))
            eng = info.get("properties", {}).get("english", "")
            return {"question": question, "answer": eng or "Not found",
                    "explanation": str(info.get("properties", {}))}

        return {"question": question, "answer": None,
                "explanation": "Question not understood. Try: 'plural of X', "
                               "'class of X', 'agent noun of X', 'meaning of X'"}

    def stats(self) -> dict:
        """Return graph statistics."""
        type_counts: dict[str, int] = {}
        for n in self._nodes.values():
            type_counts[n.type] = type_counts.get(n.type, 0) + 1
        rel_counts: dict[str, int] = {}
        for e in self._edges:
            rel_counts[e.rel] = rel_counts.get(e.rel, 0) + 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types":  type_counts,
            "edge_types":  rel_counts,
        }

    def to_json(self, path: str | None = None) -> str:
        data = {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "stats": self.stats(),
        }
        out = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            Path(path).write_text(out, encoding="utf-8")
        return out


# ── Singleton ─────────────────────────────────────────────────────────────────
_kg_instance: LinguisticKG | None = None

def get_kg() -> LinguisticKG:
    """Return the singleton knowledge graph, building it on first call."""
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = LinguisticKG().build()
    return _kg_instance
