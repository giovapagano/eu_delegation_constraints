# ============================================================
# # scripts/05_script_pipeline_main.py
# ============================================================
"""
Full pipeline for processing and classifying EurLex legal sentences.

This script:
- Loads spaCy's English model
- Adds a custom NER model for institutional actors
- Adds rule-based matcher components for verbs and nouns
- Loads external helper functions for extraction and classification
- Runs full annotation and export to CSV/JSONL
"""

import os
import sys
import json
import csv
import timeit
from pathlib import Path
import spacy
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

# ============================================================
# --- Path setup and imports ---
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# from replication_src.eurlex_functions import *

## Function to separate coordinated sentences

# The `segment_sentence_into_chunks` function is designed to process and segment sentences into smaller chunks based on coordinated conjunctions.

def segment_sentence_into_chunks(sentence):
    seen_words = set()
    sentence_root = sentence.root
    conjunction_heads = [child for child in sentence_root.children if (child.dep_ == 'conj'
                                                                       and (child.pos_ == 'AUX' or child.pos_ == 'VERB'))] # added
    sentence_chunks = []

    for conjunction_head in conjunction_heads:
        words_in_chunk = [word for word in conjunction_head.subtree]
        for word in words_in_chunk:
            seen_words.add(word)

        chunk_text = ' '.join([word.text for word in words_in_chunk])
        sentence_chunks.append(chunk_text)

    unseen_words = [word for word in sentence if word not in seen_words]
    unseen_chunk_text = ' '.join([word.text for word in unseen_words])
    sentence_chunks.append(unseen_chunk_text)
    sentence_chunks.reverse()  # Reversing the order of chunks

    return sentence_chunks

"""## Functions for the extraction of the syntactic components

This code defines a series of functions for extracting specific syntactic components from sentences using the spaCy library. These components include the root of a sentence, its children, subjects, direct objects, agents, prepositional objects, compounds, and specific types of entities like committees and representatives.
"""

## Root of the sentence and its children
def extract_root(sentence):
    root_token = sentence.root
    return root_token

def extract_children(root):
            for child in root.children:
                return child.dep_

## Actors as subjects, direct objects, and prepositional objects, associated with the NER actors
def find_subj(root):
    for child in root.children:
        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'nsubj'):
            return child.ent_type_
        elif (child.dep_ == 'nsubj' and child.pos_ == 'PRON'):
          for child in root.children:
            if ((child.dep_ == 'advcl' and (child.pos_ == 'AUX' or child.pos_ == 'VERB')) # When the Commission decides that it is no longer justified, it shall declare an end to the emergency.
                 or (child.dep_ == 'nsubj' and child.pos_ == 'PRON')): # Any of the Member States concerned may decide
              ptoken = child
              for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass')):
                  return child.ent_type_
                elif (child.dep_ == 'prep' and child.pos_ == 'ADP'):
                      ptoken2 = child
                      for child in ptoken2.children:
                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'pobj')):
                          return child.ent_type_
        elif ((child.dep_ == 'nsubj' and (child.pos_ == 'VERB' or child.pos_ == 'ADJ')) or (child.dep_ == 'csubj' and child.pos_ == 'VERB')): # The Member State concerned (belonging to the group) may decide."
              ptoken3 = child
              for child in ptoken3.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'nsubj' or child.dep_ == 'npadvmod')): # The Member State responsible may decide."
                  return child.ent_type_

def find_subj2(root): # The Commission and the Member States shall cooperate."
      for child in root.children:
        if (child.dep_ == 'nsubj'):
          ptoken = child
          for child in ptoken.children:
            if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'conj'):
                  return child.ent_type_

def find_subjpass(root):
    for child in root.children:
        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'nsubjpass'):
            return child.ent_type_
        elif (child.dep_ == 'nsubjpass' and child.pos_ == 'PRON'):
          for child in root.children:
            if ((child.dep_ == 'advcl' and (child.pos_ == 'AUX' or child.pos_ == 'VERB')) # When the Commission decides that it is no longer justified, it shall be empowered.
                 or (child.dep_ == 'nsubjpass' and child.pos_ == 'PRON')): # Any of the Member States concerned may be entitled
              ptoken = child
              for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass')):
                  return child.ent_type_
                elif (child.dep_ == 'prep' and child.pos_ == 'ADP'):
                      ptoken2 = child
                      for child in ptoken2.children:
                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'pobj')):
                          return child.ent_type_
        elif ((child.dep_ == 'nsubjpass' and (child.pos_ == 'VERB' or child.pos_ == 'ADJ')) or (child.dep_ == 'csubjpass' and child.pos_ == 'VERB')): # The Member State concerned (belonging to the group) may/shall be authorized."
              ptoken3 = child
              for child in ptoken3.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'nsubj' or child.dep_ == 'npadvmod')): # The Member State responsible may be authorized."
                  return child.ent_type_

def find_subjpass2(root): # Member States and the Agency shall not be prevented from taking any action necessary."
      for child in root.children:
        if (child.dep_ == 'nsubjpass'):
          ptoken = child
          for child in ptoken.children:
            if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'conj'):
                  return child.ent_type_

def find_dobj(root):
    for child in root.children:
        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'dobj'):
            return child.ent_type_

def find_dobj2(root): # It shall not prevent the Member States and the Agency from taking any action necessary."
      for child in root.children:
        if (child.dep_ == 'dobj'):
          ptoken = child
          for child in ptoken.children:
            if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'conj'):
                  return child.ent_type_

def find_agent(root): # e.g. "It may be applied by the Member States"
    for child in root.children:
        if (child.dep_ == 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']):
                    return child.ent_type_

def find_agent2(root):
    for child in root.children:
        if (child.dep_ == 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj'): # "The activities... shall be coordinated by the Commission and the Member States"
                  ptoken2 = child
                  for child in ptoken2.children:
                      if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'conj'):
                              return child.ent_type_
                elif (child.dep_ == 'conj' and child.text == 'by'): # " The data ...may not be used by the Commission or by a Member State"
                  ptoken3 = child
                  for child in ptoken3.children:
                      if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                              return child.ent_type_


def find_pobj(root): # e.g. "It may be applied by/to the Member States"
    for child in root.children:
        if (child.dep_ == 'prep' or child.dep_ == 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                    and child.dep_ == 'pobj'):
                        return child.ent_type_

def find_pobj2(root): # e.g. "The laws of the Member States may provide"
    for child in root.children:
        if (child.dep_ == 'dobj' or child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'oprd'): # It shall be kept informed (oprd) by
            ptoken = child
            for child in ptoken.children:
                if (child.dep_== 'prep' or child.dep_== 'agent'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                            and child.dep_ == 'pobj'):
                                return child.ent_type_

def find_pobj2subj(root): # e.g. "The laws of the Member States may provide"
    for child in root.children:
        if (child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_== 'prep' or child.dep_== 'agent'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                            and child.dep_ == 'pobj'):
                                return child.ent_type_

def find_pobj2dobj(root): # e.g. "It shall not affect the right of the Member States"
    for child in root.children:
        if (child.dep_ == 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_== 'prep' or child.dep_== 'agent'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                            and child.dep_ == 'pobj'):
                                return child.ent_type_

def find_pobj3(root): # e.g. "It shall not be set by the laws of the Member States"
    for child in root.children:
        if (child.dep_== 'prep' or child.dep_== 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'prep' or child.dep_== 'agent'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                    and child.dep_ == 'pobj'):
                                      return child.ent_type_

def find_pobj4(root): # e.g. "The measure decided upon by the Commission shall set"
    for child in root.children:
        if (child.dep_== 'nsubj' or child.dep_== 'nsubjpass' or child.dep_== 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'acl'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'agent'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                   and child.dep_ == 'pobj'):
                                    return child.ent_type_

def find_pobj5(root): # e.g. "It may be set by a decision taken by the Commission."
    for child in root.children: # "... acting on a proposal from the Commission"
        if (child.dep_== 'agent' or child.dep_== 'advcl' or child.dep_== 'dobj'): # It shall have no effect on decisions of Member States
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj' or child.dep_== 'prep'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'acl' or child.dep_== 'pobj'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.dep_== 'agent' or child.dep_== 'prep'):
                                  ptoken4 = child
                                  for child in ptoken4.children:
                                    if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                        and child.dep_ == 'pobj'):
                                          return child.ent_type_

def find_pobj6(root): # e.g. "The Council may decide on the basis of the proposal from the Commission."
    for child in root.children:
        if (child.dep_== 'agent' or child.dep_== 'advcl' or child.dep_== 'prep'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj' or child.dep_== 'prep'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'acl' or child.dep_== 'pobj' or child.dep_== 'prep'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'pobj'):
                                  ptoken4 = child
                                  for child in ptoken4.children:
                                    if (child.dep_== 'prep' or child.dep== 'pobj'):
                                       ptoken5 = child
                                       for child in ptoken5.children:
                                        if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                            and child.dep_ == 'pobj'):
                                              return child.ent_type_

def find_pobj7(root): # e.g. "The Council may decide, acting on the basis of the proposal from the Commission."
    for child in root.children:
        if (child.dep_== 'advcl'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_== 'prep'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'pobj'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.dep_== 'prep'):
                                  ptoken4 = child
                                  for child in ptoken4.children:
                                    if (child.dep_ == 'pobj'):
                                       ptoken5 = child
                                       for child in ptoken5.children:
                                        if (child.dep_== 'prep'):
                                              ptoken6 = child
                                              for child in ptoken6.children:
                                                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                                    and child.dep_ == 'pobj'):
                                                        return child.ent_type_

def find_compound(root):
    for child in root.children: # e.g. "The Commission decision may establish"
        if (child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_== 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                    and child.dep_ == 'compound'):
                         return child.ent_type_
        elif (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'advcl'): # e.g. "It may be established by the Commission decision"
               ptoken2 = child
               for child in ptoken2.children:
                   if (child.dep_ == 'pobj' or child.dep_ == 'prep'):
                      ptoken3 = child
                      for child in ptoken3.children:
                          if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                              and child.dep_ == 'compound'):
                                   return child.ent_type_
                          elif (child.dep_ == 'prep' or child.dep_ == 'pobj'):
                              ptoken4 = child
                              for child in ptoken4.children: # e.g. ".. acting on a Commission proposal"
                                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                    and child.dep_ == 'compound'):
                                    return child.ent_type_
                                elif (child.dep_ == 'pobj' or child.dep_ == 'prep'):
                                  ptoken5 = child
                                  for child in ptoken5.children: # e.g. ".. on the basis of a Commission proposal"
                                    if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                        and child.dep_ == 'compound'):
                                          return child.ent_type_
                                    elif (child.dep_ == 'pobj'):
                                       ptoken6 = child
                                       for child in ptoken6.children: # e.g. ".. acting on the basis of a Commission proposal"
                                          if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                                              and child.dep_ == 'compound'):
                                                 return child.ent_type_

def find_compound_subj(root): # to address a dependency parser error
    for child in root.children: # e.g. "The power to adopt standards is conferred on the Commission subject to"
        if (child.dep_ == 'prep'):
            ptoken = child
            for child in ptoken.children:
                  if (child.dep_ == 'pobj' and child.text == 'subject'):
                      ptoken2 = child
                      for child in ptoken2.children:
                          if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA']
                              and child.dep_ == 'compound'):
                                   return child.ent_type_

## Other generic actors
def find_board_dobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and (child.text == 'board' or child.text == 'Board')):
                    return True

def find_committee(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj')
                and (child.text == 'committee' or child.text == 'Committee')):
                    return True
        elif (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'advcl'):
              ptoken = child
              for child in ptoken.children:
                  if (child.dep_ == 'pobj' and (child.text == 'committee' or child.text == 'Committee')):
                      return True
                  elif (child.dep_== 'agent'):
                    ptoken2 = child # 'The Commission, assisted by a committee, shall'
                    for child in ptoken2.children:
                      if (child.dep_ == 'pobj' and (child.text == 'committee' or child.text == 'Committee')):
                          return True
                  elif (child.dep_== 'pobj'):
                    ptoken3 = child
                    for child in ptoken3.children:
                      if (child.dep_ =='acl'):
                        ptoken4 = child
                        for child in ptoken4.children:
                          if (child.dep_== 'agent'):
                            ptoken5 = child # '.. by the Commission assisted by a committee'
                            for child in ptoken5.children:
                              if (child.dep_ == 'pobj' and (child.text == 'committee' or child.text == 'Committee')):
                                return True

def find_committee_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass')
                and (child.text == 'committee' or child.text == 'Committee')):
                    return True

def find_committee_agent(root):
    for child in root.children:
        if (child.dep_ == 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj' and (child.text == 'committee' or child.text == 'Committee')):
                    return True

def find_committee_pobj(root):
    for child in root.children:
         if (child.dep_ == 'prep' and child.text =='to'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj' and (child.text == 'committee' or child.text == 'Committee')):
                    return True

def find_rep(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj')
             and child.ent_type_ in ['REPRESENTATIVE']):
                return True
        elif (child.dep_== 'agent' or child.dep_== 'prep'):
                ptoken = child
                for child in ptoken.children:
                    if (child.dep_ == 'pobj' and child.ent_type_ in ['REPRESENTATIVE']):
                                return True

def find_rep_subj(root):
    for child in root.children:
        if (child.dep_ == 'nsubj' and child.ent_type_ in ['REPRESENTATIVE']):
            ptoken = child
            for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'compound' or child.dep_ == 'poss')): # Commission representative
                  return child.ent_type_
                elif (child.dep_ == 'prep' and (child.text == 'of' or child.text == 'from')): # Representative of the Commission
                      ptoken2 = child
                      for child in ptoken2.children:
                          if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                            return child.ent_type_
                elif (child.dep_ == 'conj'): # Officials or authorised representatives of the Member State
                      ptoken3 = child
                      for child in ptoken3.children:
                          if (child.ent_type_ in ['REPRESENTATIVE']):
                              ptoken4 = child
                              for child in ptoken4.children:
                                  if (child.dep_ == 'prep' and (child.text == 'of' or child.text == 'from')):
                                        ptoken5 = child
                                        for child in ptoken5.children:
                                            if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                                                return child.ent_type_

def find_rep_subjpass(root):
    for child in root.children:
        if (child.dep_ == 'nsubjpass' and child.ent_type_ in ['REPRESENTATIVE']):
            ptoken = child
            for child in ptoken.children:
                if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'compound' or child.dep_ == 'poss')): # Commission representative
                  return child.ent_type_
                elif (child.dep_ == 'prep' and (child.text == 'of' or child.text == 'from')): # Representative of the Commission
                      ptoken2 = child
                      for child in ptoken2.children:
                          if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                            return child.ent_type_
                elif (child.dep_ == 'conj'): # Officials or authorised representatives of the Member State
                      ptoken3 = child
                      for child in ptoken3.children:
                          if (child.ent_type_ in ['REPRESENTATIVE']):
                              ptoken4 = child
                              for child in ptoken4.children:
                                  if (child.dep_ == 'prep' and (child.text == 'of' or child.text == 'from')):
                                        ptoken5 = child
                                        for child in ptoken5.children:
                                            if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                                                return child.ent_type_

def find_rep_agent(root):
    for child in root.children:
        if (child.dep_== 'agent'):
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['REPRESENTATIVE']):
                     ptoken = child
                     for child in ptoken.children:
                         if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and (child.dep_ == 'compound' or child.dep_ == 'poss')): # by Commission representative
                             return child.ent_type_
                         elif (child.dep_ == 'prep' and (child.text == 'of' or child.text == 'from')): # by representative of the Commission
                              ptoken2 = child
                              for child in ptoken2.children:
                                  if (child.ent_type_ in ['COM', 'AGE', 'MS', 'CA'] and child.dep_ == 'pobj'):
                                      return child.ent_type_

## Definitions for "Nothing" and "No provision(s)" as subject
def find_nothing(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass')
           and (child.text =='nothing' or child.text =='Nothing')):
            return True
        elif ((child.dep_ == 'nsubj'  or child.dep_ == 'nsubjpass')
            and (child.text =='provision' or child.text =='provisions')):
              ptoken = child
              for child in ptoken.children:
                  if (child.dep_ == 'det' and (child.text =='no' or child.text =='No')):
                      return True

## Definitions for verbs, associated with the NER verbs
def find_root(sentence):
    if sentence.root.ent_type_ in ["SOFT_IMPL", "DELEGATION", "PERMISSION", "CONSTRAINT", "ACTIVE_CONSTRAINT"]:
        return sentence.root.ent_type_

## Auxiliaries
def find_aux(root):
        for child in root.children:
            if (child.dep_ == 'aux'):
                return True

def find_auxpass(root):
        for child in root.children:
            if (child.dep_ == 'auxpass'):
                return True

## Permissive and strict modal verbs
def find_pmod(root):
        for child in root.children:
            if (child.dep_ == 'aux'
                and (child.text =='may' or child.text =='can')):
                return True

def find_smod(root):
        for child in root.children:
            if (child.dep_ == 'aux'
                and (child.text =='shall' or child.text =='must' or child.text =='will')):
                return True

## Definitions concerning "need not" (semi-modal verb)
# Need as auxiliary: "Member states need not apply"
def find_needaux(root):
        for child in root.children:
            if (child.dep_ == 'aux'
                and (child.text =='need' or child.text =='needs')):
                return True

# Need as root verb: "Member states need not to apply"
def find_needroot(sentence):
    if (sentence.root.text =='need' or sentence.root.text =='needs') :
          return True

# Negation modifier when Need is a root verb: "Member states need not to apply"
def find_needneg(root):
        for child in root.children:
            if (child.dep_ == 'xcomp'):
                ptoken = child
                for child in ptoken.children:
                    if (child.dep_ == 'neg'):
                        return True

## "Be" as root verb
def find_be(sentence):
    if (sentence.root.text =='be' or sentence.root.text =='is'
        or sentence.root.text =='are'):
          return True

## Delextical verbs "Have", "Give", "Make" and "Take" as root verbs
def find_have(sentence):
    if (sentence.root.text =='have' or sentence.root.text =='has'):
          return True
def find_give(sentence):
    if (sentence.root.text =='give' or sentence.root.text =='given'):
          return True
def find_make(sentence):
    if (sentence.root.text =='make' or sentence.root.text =='made'):
          return True
def find_take(sentence):
    if (sentence.root.text =='take' or sentence.root.text =='taken'):
          return True

## Verbs associated with procedural features (e.g. proposal, control)
def find_assist(sentence):
    if (sentence.root.text =='assist' or sentence.root.text =='assisted'):
          return True
def find_draw(sentence):
    if (sentence.root.text =='draw' or sentence.root.text =='drawn'):
          return True
def find_enter(sentence):
    if (sentence.root.text =='enter' or sentence.root.text =='entered'
        or sentence.root.text =='hold' or sentence.root.text =='held'
        or sentence.root.text =='conduct' or sentence.root.text =='conduct'
        or sentence.root.text =='launch' or sentence.root.text =='launched'
        or sentence.root.text =='start' or sentence.root.text =='started'):
          return True
def find_prepare(sentence):
    if (sentence.root.text =='prepare' or sentence.root.text =='prepared'
        or sentence.root.text =='produce' or sentence.root.text =='produced'):
          return True
def find_provide(sentence):
    if (sentence.root.text =='provide' or sentence.root.text =='provided'
        or sentence.root.text =='exchange' or sentence.root.text =='exchanged'
        or sentence.root.text =='supply' or sentence.root.text =='supplied'):
          return True
def find_propose(sentence):
    if (sentence.root.text =='propose' or sentence.root.text =='proposed'):
          return True
def find_propose2(root): # 'whether to propose'
        for child in root.children:
            if (child.pos_ == 'VERB' and child.text =='propose'):
                return True
            elif (child.dep_ == 'prep' or child.dep_ =='mark'):
                ptoken = child
                for child in ptoken.children:
                    if (child.pos_ == 'VERB' and child.text =='propose'):
                        return True

def find_put(sentence):
    if (sentence.root.text =='put'):
            return True

def find_forward(root):
    for child in root.children:
        if (child.dep_ == 'advmod' and child.text =='forward'):
             return True

def find_refer(sentence):
    if (sentence.root.text =='refer' or sentence.root.text =='referred'
        or sentence.root.text =='bring' or sentence.root.text =='brought'):
          return True

def find_submit(sentence):
    if (sentence.root.text =='submit' or sentence.root.text =='submitted'
        or sentence.root.text =='present' or sentence.root.text =='presented'):
            return True

# Verbs associated with rights, measures and their consequences
def find_adopt(sentence):
    if (sentence.root.text =='adopt' or sentence.root.text =='adopted'):
          return True
def find_affect(sentence):
    if (sentence.root.text =='affect' or sentence.root.text =='preclude'
        or sentence.root.text =='prejudice'):
          return True
def find_apply(sentence):
    if (sentence.root.text =='apply' or sentence.root.text =='applied'):
          return True
def find_issueroot(sentence):
    if (sentence.root.text =='issue' or sentence.root.text =='issued'
        or sentence.root.text =='deliver' or sentence.root.text =='delivered'):
          return True
def find_remain(sentence):
    if (sentence.root.text =='remain' or sentence.root.text =='remains'):
          return True
def find_retain(sentence):
    if (sentence.root.text =='retain' or sentence.root.text =='retains'
        or sentence.root.text =='reserve' or sentence.root.text =='reserves'):
          return True

## Negation modifier
def find_neg(root):
        for child in root.children:
            if (child.dep_ == 'neg'):
                return True
            elif (child.dep_== 'nsubj' or child.dep_== 'nsubjpass'):  # e.g. "No Member State may"
              ptoken = child
              for child in ptoken.children:
                if (child.dep_ == 'det' and (child.text =='No' or child.text =='no')):
                  return True
            elif (child.dep_== 'advmod' and (child.text =='longer' or child.text =='more')):  # e.g. "Member States shall no longer/more be obliged"
              ptoken = child
              for child in ptoken.children:
                if (child.dep_ == 'neg' and child.text =='no'):
                  return True
            elif (child.dep_== 'dobj' and child.ent_type_ in ['RIGHT']):  # e.g. "Commission officials shall have no powers"
              ptoken = child
              for child in ptoken.children:
                if (child.dep_ == 'det' and child.text =='no'):
                  return True


## Preposition "by" introducing the agent
def find_by(root):
        for child in root.children:
            if (child.dep_ == 'agent'):
                return True

def find_by2(root): # e.g. "The measure decided upon by the Commission shall set"
    for child in root.children:
        if (child.dep_== 'nsubj' or child.dep_== 'nsubjpass' or child.dep_== 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'acl'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'agent'):
                            return True
        elif (child.dep_== 'advcl' or child.dep_ == 'oprd' ):   # e.g. "The Commission, assisted by.., shall"  "It shall be kept informed by"
            ptoken3 = child
            for child in ptoken3.children:
              if (child.dep_== 'agent'):
                return True


def find_by3(root): # e.g. "It may be set by a decision taken by the Commission."
    for child in root.children:
        if (child.dep_== 'agent'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if (child.dep_== 'acl'):
                            ptoken3 = child
                            for child in ptoken3.children:
                                if (child.dep_== 'agent'):
                                    return True
## Preposition "to"
def find_to(root):
        for child in root.children:
            if (child.dep_ == 'prep' and child.text =='to'):
                return True

def find_to2(root):
        for child in root.children:
            if (child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj'):
                ptoken = child
                for child in ptoken.children:
                  if (child.dep_ == 'prep' and child.text =='to'):
                    return True

## Terms associated with prerogatives and competences
def find_competent(root):
    for child in root.children:
        if (child.dep_ == 'acomp' and child.text =='competent'):
                    return True

def find_force(root): # "in force"
    for child in root.children:
        if (child.dep_ == 'prep' and child.text == 'in'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'pobj' and child.text == 'force'):
                        return True
def find_free(root):
    for child in root.children:
        if (child.dep_ == 'acomp'
            and (child.text =='free' or child.text =='exempt')):
                    return True

def find_noeffect(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and (child.text == 'effect' or child.text == 'impact')):
           ptoken = child
           for child in ptoken.children:
               if (child.dep_ == 'det' and child.text == 'no'):
                   return True

def find_prejudice(root):
    for child in root.children:
        if (child.dep_ == 'prep' and (child.text =='without' or child.text =='Without')):
          ptoken = child
          for child in ptoken.children:
            if (child.dep_ == 'pobj' and child.text =='prejudice'):
                    return True

def find_accountable(root):
    for child in root.children:
        if (child.dep_ == 'acomp' and (child.text == 'accountable' or child.text == 'subject' or child.text == 'liable' )):
             return True

def find_responsible(root):
    for child in root.children:
        if (child.dep_ == 'acomp' and child.text == 'responsible'):
             return True

def find_right(root):
    for child in root.children:
        if ((child.dep_ == 'dobj' or child.dep_ == 'nsubjpass')
                and child.ent_type_ in ['RIGHT']):
                        return True
        elif (child.dep_ == 'dobj' or child.dep_ == 'prep'):
           ptoken = child
           for child in ptoken.children:
               if ((child.dep_ == 'pobj' or child.dep_ == 'conj') and child.ent_type_ in ['RIGHT']): # CA shall have, in accordance with national law, the following powers.
                        return True
               elif (child.dep_ == 'pobj'): # without prejudice to the right
                ptoken2 = child
                for child in ptoken2.children:
                  if (child.dep_ == 'prep'):
                    ptoken3 = child
                    for child in ptoken3.children:
                        if (child.dep_ == 'pobj' and child.ent_type_ in ['RIGHT']):
                           return True

def find_right_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass') and child.ent_type_ in ['RIGHT']):
              return True

def find_right_dobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.ent_type_ in ['RIGHT']):
              return True

## Terms associated with legal and non-legal instruments, measures and actions
# Proposals
def find_proposal(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj') # nsubj added, sure?
                and child.ent_type_ in ['PROPOSAL']):
                    return True
        elif (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'advcl'): # added pobj, sure?
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                        return True
                elif (child.dep_ == 'prep'):
                      ptoken2 = child
                      for child in ptoken2.children:
                            if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                return True
                            elif (child.dep_ == 'pobj'):
                              ptoken3 = child
                              for child in ptoken3.children:
                                if (child.dep_ == 'prep'):
                                  ptoken4 = child
                                  for child in ptoken4.children:
                                    if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                             return True
                elif (child.dep_ == 'pobj'):
                      ptoken5 = child
                      for child in ptoken5.children:
                            if (child.dep_ == 'prep'):
                              ptoken6 = child
                              for child in ptoken6.children:
                                if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                    return True

def find_proposal_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass') and child.ent_type_ in ['PROPOSAL']):
             return True

def find_proposal_dobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.ent_type_ in ['PROPOSAL']):
                    return True
        elif (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'advcl'): # e.g. Commission shall submit to the Council proposals
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                        return True
                elif (child.dep_ == 'prep'):
                      ptoken2 = child
                      for child in ptoken2.children:
                            if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                return True
                            elif (child.dep_ == 'pobj'):
                              ptoken3 = child
                              for child in ptoken3.children:
                                if (child.dep_ == 'prep'):
                                  ptoken4 = child
                                  for child in ptoken4.children:
                                    if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                             return True
                elif (child.dep_ == 'pobj'):
                      ptoken5 = child
                      for child in ptoken5.children:
                            if (child.dep_ == 'prep'):
                              ptoken6 = child
                              for child in ptoken6.children:
                                if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                    return True

def find_legprop(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj') # nsubj added, sure?
                and child.ent_type_ in ['PROPOSAL']):
                    ptoken = child
                    for child in ptoken.children:
                      if (child.text == 'legislative'):
                        return True
        elif (child.dep_== 'agent' or child.dep_== 'prep' or child.dep_== 'advcl'): # added pobj, sure?
                    ptoken2 = child
                    for child in ptoken2.children:
                        if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                             ptoken3 = child
                             for child in ptoken3.children:
                              if (child.text == 'legislative'):
                                return True
                        elif (child.dep_ == 'prep'):
                          ptoken4 = child
                          for child in ptoken4.children:
                            if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                               ptoken5 = child
                               for child in ptoken5.children:
                                if (child.text == 'legislative'):
                                  return True
                            elif (child.dep_ == 'pobj'):
                              ptoken6 = child
                              for child in ptoken6.children:
                                if (child.dep_ == 'prep'):
                                  ptoken7 = child
                                  for child in ptoken7.children:
                                    if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                      ptoken8 = child
                                      for child in ptoken8.children:
                                        if (child.text == 'legislative'):
                                          return True
                        elif (child.dep_ == 'pobj'):
                          ptoken9 = child
                          for child in ptoken9.children:
                            if (child.dep_ == 'prep'):
                              ptoken10 = child
                              for child in ptoken10.children:
                                if ((child.dep_ == 'pobj') and child.ent_type_ in ['PROPOSAL']):
                                  ptoken11 = child
                                  for child in ptoken11.children:
                                    if (child.text == 'legislative'):
                                      return True

# Other article 288 (TFEU) secondary instruments, such as regulations and directives, could be included
# but they are captured by the definition of 'proposal' or 'legislative proposal' or the more general extraction rules

# Recommendations
def find_recommendation(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj') # nsubj added, sure?
                and child.ent_type_ in ['RECOMMENDATION']):
                    return True
        elif (child.dep_== 'agent' or child.dep_== 'prep'): # added pobj, sure?
                    ptoken = child
                    for child in ptoken.children:
                        if ((child.dep_ == 'pobj') and child.ent_type_ in ['RECOMMENDATION']):
                                return True

def find_recommendation_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass') and child.ent_type_ in ['RECOMMENDATION']):
             return True

def find_recommendation_dobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.ent_type_ in ['RECOMMENDATION']):
            return True
        elif (child.dep_== 'agent' or child.dep_== 'prep'): # e.g. Commission shall submit to the Council recommendations
                    ptoken = child
                    for child in ptoken.children:
                        if ((child.dep_ == 'pobj') and child.ent_type_ in ['RECOMMENDATION']):
                                return True

def find_recommendation_pobj(root):
    for child in root.children:
        if (child.dep_== 'agent' or child.dep_== 'prep'):
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['RECOMMENDATION']):
                                return True

# Opinions
def find_opinion(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj') # nsubj added, sure?
                and child.ent_type_ in ['OPINION']):
                    return True
        elif ((child.dep_== 'agent') or (child.dep_== 'prep')): # added pobj, sure?
                    ptoken = child
                    for child in ptoken.children:
                        if ((child.dep_ == 'pobj')
                           and child.ent_type_ in ['OPINION']):
                                return True

def find_opinion_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass') and child.ent_type_ in ['OPINION']):
                    return True

def find_opinion_dobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.ent_type_ in ['OPINION']):
                    return True

def find_opinion_pobj(root):
    for child in root.children:
        if (child.dep_== 'agent' or child.dep_== 'prep'):
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['OPINION']):
                                return True

# Measures and similia
def find_measure(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj')
                and child.ent_type_ in ['MEASURE']):
                       return True
        elif ((child.dep_== 'agent' or child.dep_== 'prep')): # added pobj, sure?
                    ptoken = child
                    for child in ptoken.children:
                        if ((child.dep_ == 'pobj') and child.ent_type_ in ['MEASURE']):
                                return True

def find_measure_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass')
                and child.ent_type_ in ['MEASURE']):
                       return True

def find_measure_dobj(root):
    for child in root.children:
        if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                       return True

def find_measure_pobj(root):
    for child in root.children:
        if (child.dep_== 'agent' or child.dep_== 'prep'):
              ptoken = child
              for child in ptoken.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['MEASURE']):
                                return True

def find_measure_pobj2(root): # e.g. It shall have no effect on decisions
    for child in root.children:
        if (child.dep_ == 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_== 'prep'):
                    ptoken2 = child
                    for child in ptoken2.children:
                        if ((child.dep_ == 'pobj') and child.ent_type_ in ['MEASURE']):
                                return True

# Article 290 (TFEU) tertiary instruments (incl. implementing/delegated acts: regulation, directive, decision)
def find_teract(root):
    for child in root.children: # e.g. "Delegated acts shall be" "The Commission shall adopt delegated acts"
        if ((child.dep_ == 'nsubjpass' or child.dep_ == 'dobj') # "The Commission shall an implementing delegated act"
              and child.ent_type_ in ['MEASURE']):
               ptoken = child
               for child in ptoken.children:
                   if ((child.dep_ == 'amod')
                      and (child.text =='delegated' or child.text == 'implementing' or child.text =='technical'
                           or child.text =='Delegated' or child.text == 'Implementing' or child.text =='Technical')):
                              return True
        elif (child.dep_ == 'nsubjpass' or child.dep_ == 'dobj'):
              ptoken2 = child
              for child in ptoken2.children:
                 if (child.dep_ == 'acl' and child.text == 'implementing'): # e.g. "Those implementing acts shall be"
                    ptoken3 = child
                    for child in ptoken3.children:
                          if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                                   return True
                 elif (child.dep_ == 'acl' or child.dep_ == 'relcl'):
                        ptoken4 = child
                        for child in ptoken4.children:  # "The power(s) to adopt delegated acts" (power(s) -> acl/relcl)
                          if ((child.dep_ == 'dobj') # "It confers the power to adopt" (power in singular). "Power(s) to adopt delegated acts is/are conferred."
                              and child.ent_type_ in ['MEASURE']):
                                  ptoken5 = child
                                  for child in ptoken5.children:
                                      if ((child.dep_ == 'amod')
                                      and (child.text =='delegated' or child.text == 'implementing' or child.text =='technical'
                                         or child.text =='Delegated' or child.text == 'Implementing' or child.text =='Technical')):
                                             return True
                          elif (child.dep_ == 'xcomp' and child.text == 'implementing'): # e.g. "The power(s) to adopt implementing acts is/are"
                                 ptoken6 = child # "Power(s) to adopt implementing acts is/are conferred." "It confers on the Com. the power(s) to adopt impl. acts"
                                 for child in ptoken6.children: # "It confers the power to adopt implementing acts on the Commission." (power in singular)
                                  if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                                          return True
        elif (child.dep_ == 'xcomp' and child.text == 'implementing'): # e.g. "The Commission shall adopt implementing acts"
               ptoken7 = child
               for child in ptoken7.children:
                if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                            return True
        elif (child.dep_== 'xcomp'):
               ptoken8 = child # e.g. "Power(s) is/are conferred on the Commission to adopt delegated acts"
               for child in ptoken8.children: # "It confers the powers to adopt" (powers in plural)
                   if ((child.dep_ == 'pobj' or child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                            ptoken9 = child
                            for child in ptoken9.children:
                                if ((child.dep_ == 'amod')
                                and (child.text =='delegated' or child.text == 'implementing' or child.text =='technical')):
                                      return True
                   elif (child.dep_ == 'xcomp' and child.text == 'implementing'): # e.g. "Power(s) is/are conferred on the Commission to adopt implementing acts"
                         ptoken10 = child # "It confers the powers to adopt implementing acts on the Commission." (powers in plural)
                         for child in ptoken10.children:
                           if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                                return True
        elif (child.dep_== 'prep'):
               ptoken11 = child
               for child in ptoken11.children:
                if (child.dep_=='pobj'):
                    ptoken12 = child
                    for child in ptoken12.children:
                      if (child.dep_=='prep'):
                          ptoken13 = child
                          for child in ptoken13.children: # e.g. "... by way of delegated acts..."
                            if ((child.dep_ == 'pobj' or child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                                   ptoken14 = child
                                   for child in ptoken14.children:
                                    if ((child.dep_ == 'amod')
                                    and (child.text =='delegated' or child.text == 'implementing' or child.text =='technical')):
                                        return True
                            elif (child.dep_ == 'pcomp' and child.text == 'implementing'):
                              ptoken15 = child # e.g. "... by way of implementing acts..."
                              for child in ptoken15.children:
                                if ((child.dep_ == 'dobj') and child.ent_type_ in ['MEASURE']):
                                       return True

# Other measures: interinstitutional agreement, resolution, conclusion, communication, green paper and white papers
# CFSP legal instruments: EU actions and positions
# Summary table of legal instrument: https://publications.europa.eu/code/en/en-130800-tab.htm#structure

## Terms associated with obligations, constraints and information provision
def find_secrecy(root): # e.g. "the obligation of ... shall apply to"
    for child in root.children:
        if (child.dep_ == 'nsubj' or child.dep_ == 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if (child.dep_ == 'prep'):
                    ptoken2 = child
                    for child in ptoken2.children:
                      if (child.dep_ == 'pobj' and child.text == 'secrecy'):
                          return True

def find_issue(root): # e.g. "..refer the issue"
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj')
                and child.ent_type_ in ['ISSUE']):
                    return True

def find_information(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass' or child.dep_ == 'dobj')
            and child.ent_type_ in ['INFORMATION']):
                    return True
        elif (child.dep_ == 'prep'):
            ptoken = child
            for child in ptoken.children:
                if ((child.dep_ == 'pobj')
                and child.ent_type_ in ['INFORMATION']):
                        return True

def find_information_subj(root):
    for child in root.children:
        if ((child.dep_ == 'nsubj' or child.dep_ == 'nsubjpass') and child.ent_type_ in ['INFORMATION']):
                    return True

def find_information_dobjpobj(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.ent_type_ in ['INFORMATION']):
                    return True
        elif (child.dep_ == 'dobj'):
            ptoken = child
            for child in ptoken.children:
                if ((child.dep_ == 'compound') and child.ent_type_ in ['INFORMATION']):
                      return True
                elif (child.dep_ == 'acl' and child.pos_ == 'VERB'):
                      ptoken5 = child
                      for child in ptoken5.children:
                          if (child.dep_ == 'prep'):
                              ptoken6 = child
                              for child in ptoken6.children:
                                  if ((child.dep_ == 'pobj') and child.ent_type_ in ['INFORMATION']):
                                       return True
                elif (child.dep_== 'conj'):
                     ptoken2 = child
                     for child in ptoken2.children:
                       if (child.dep_ == 'acl' and child.pos_ == 'VERB'):
                           ptoken3 = child
                           for child in ptoken3.children:
                               if (child.dep_ == 'prep'):
                                   ptoken3 = child
                                   for child in ptoken3.children:
                                       if ((child.dep_ == 'pobj') and child.ent_type_ in ['INFORMATION']):
                                            return True
        elif (child.dep_ == 'prep'):
            ptoken4 = child
            for child in ptoken4.children:
                if ((child.dep_ == 'pobj') and child.ent_type_ in ['INFORMATION']):
                        return True

def find_public(root):
    for child in root.children:
        if (child.pos_ == 'NOUN'  and child.text =='public'): # e.g. The Authority shall make its opinion public
              return True
        elif (child.pos_ == 'ADJ'  and (child.text =='public' or child.text =='available' or child.text =='accessible')):
              return True
        elif (child.dep_ == 'ccomp' and (child.text =='available' or child.text =='accessible')):
              ptoken = child
              for child in ptoken.children:
                  if (child.dep_ == 'advmod' and child.text =='publicly'):
                     return True
        elif (child.dep_ == 'ccomp'):
              ptoken2 = child
              for child in ptoken2.children:
                  if (child.pos_ == 'ADJ' and (child.text =='public' or child.text =='available'or child.text =='accessible')):
                     return True
        elif (child.dep_ == 'dobj'):
              ptoken3 = child
              for child in ptoken3.children:
                  if (child.pos_ == 'ADJ' and (child.text =='public' or child.text =='available' or child.text =='accessible')):
                     return True
                  elif (child.dep_ == 'acl' and child.pos_ == 'VERB'):
                        ptoken4 = child
                        for child in ptoken4.children:
                          if (child.pos_ == 'ADJ' and (child.text =='public' or child.text =='available' or child.text =='accessible')):
                              return True

def find_good(root):
    for child in root.children:
        if (child.pos_ == 'ADJ'  and child.text =='good'):
              return True

## Expressions associated with constraints
def find_accordance(root):
    for child in root.children:
        if (child.dep_ == 'prep' or child.dep_ == 'dobj' or child.dep_ == 'advcl' or child.dep_=='agent' or child.dep_=='xcomp'):
                ptoken = child
                for child in ptoken.children:
                        if ((child.dep_ == 'pobj') # e.g. "The act shall be adopted in accordance" "The Commission shall adopt the act in accordance"
                           and (child.text =='accordance' or child.text =='conformity')):
                                return True
                        elif (child.dep_=='pobj' or child.dep_=='dobj' or child.dep_=='xcomp'):
                               ptoken2 = child
                               for child in ptoken2.children: # e.g. "The Comm. shall be empowered to adopt implementing acts in accordance"
                                   if (child.dep_== 'prep'):
                                            ptoken3 = child
                                            for child in ptoken3.children:
                                                if ((child.dep_ == 'pobj')
                                                   and (child.text =='accordance' or child.text =='conformity')):
                                                       return True
                                   elif (child.dep_ == 'acl'): # e.g. "The act shall be adopted by ... acting in accordance"
                                       ptoken4 = child
                                       for child in ptoken4.children:
                                          if (child.dep_== 'prep'):
                                            ptoken5 = child
                                            for child in ptoken5.children:
                                                if ((child.dep_ == 'pobj')
                                                   and (child.text =='accordance' or child.text =='conformity')):
                                                       return True
                        elif (child.dep_== 'prep'):
                              ptoken6 = child
                              for child in ptoken6.children: # e.g. "The Comm. shall be empowered to adopt delegated acts in accordance"
                                  if ((child.dep_ == 'pobj')
                                       and (child.text =='accordance' or child.text =='conformity')):
                                            return True

def find_procedure(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.text == 'procedure'):
             return True
        elif (child.dep_ == 'prep' or child.dep_ == 'dobj' or child.dep_ == 'advcl' or child.dep_ == 'agent'):
                ptoken = child
                for child in ptoken.children:
                        if (child.dep_ == 'pobj' or child.dep_ =='prep'):
                              ptoken2 = child
                              for child in ptoken2.children:
                                  if (child.dep_ == 'prep' or child.dep_ =='pobj' or child.dep_ =='acl'):
                                       ptoken3 = child
                                       for child in ptoken3.children: # e.g. "The act shall be adopted in accordance with the procedure"
                                            if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                return True
                                            elif (child.dep_ == 'prep'):
                                                  ptoken4 = child
                                                  for child in ptoken4.children:  # e.g. "The Commission shall adopt the act in accordance with the procedure"
                                                      if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                           return True
                                                      elif (child.dep_ == 'pobj'):
                                                           ptoken5 = child
                                                           for child in ptoken5.children:
                                                               if (child.dep_ == 'prep'):
                                                                   ptoken6 = child
                                                                   for child in ptoken6.children:  # e.g. "... decided by the Commission acting in accordance with the procedure"
                                                                       if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                                            return True

## Terms associated with oversight procedures (comitology)
def find_comitproc(root):
    for child in root.children:
        if (child.dep_ == 'dobj' and child.text == 'procedure'):
             ptoken = child
             for child in ptoken.children:
                 if ((child.dep_ == 'amod' and (child.text =='advisory' or child.text =='regulatory'))
                    or (child.dep_ == 'compound' and (child.text =='management' or child.text =='safeguard' or child.text =='examination'))):
                          return True
        elif (child.dep_ == 'prep' or child.dep_ == 'dobj' or child.dep_ == 'advcl' or child.dep_ == 'agent'):
                ptoken2 = child
                for child in ptoken2.children:
                        if (child.dep_ == 'pobj' or child.dep_ =='prep'):
                              ptoken3 = child
                              for child in ptoken3.children:
                                  if (child.dep_ == 'prep' or child.dep_ =='pobj' or child.dep_ =='acl'):
                                       ptoken4 = child
                                       for child in ptoken4.children:
                                            if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                 ptoken5 = child # e.g. "The act shall be adopted in accordance with the ... procedure"
                                                 for child in ptoken5.children:
                                                     if ((child.dep_ == 'amod' and (child.text =='advisory' or child.text =='regulatory'))
                                                        or (child.dep_ == 'compound' and (child.text =='management' or child.text =='safeguard' or child.text =='examination'))):
                                                            return True
                                            elif (child.dep_ == 'prep'):
                                                  ptoken6 = child # e.g. "The Commission shall adopt the act in accordance with the ... procedure"
                                                  for child in ptoken6.children:
                                                      if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                           ptoken7 = child
                                                           for child in ptoken7.children:
                                                               if ((child.dep_ == 'amod' and (child.text =='advisory' or child.text =='regulatory'))
                                                                  or (child.dep_ == 'compound' and (child.text =='management' or child.text =='safeguard' or child.text =='examination'))):
                                                                      return True
                                                      elif (child.dep_ == 'pobj'):
                                                            ptoken8 = child # e.g. "...be decided by the Commission acting in accordance with the ... procedure"
                                                            for child in ptoken8.children:
                                                              if (child.dep_ == 'prep'):
                                                                  ptoken9 = child
                                                                  for child in ptoken9.children:
                                                                     if (child.dep_ == 'pobj' and child.text =='procedure'):
                                                                        ptoken10 = child
                                                                        for child in ptoken10.children:
                                                                          if ((child.dep_ == 'amod' and (child.text =='advisory' or child.text =='regulatory'))
                                                                           or (child.dep_ == 'compound' and (child.text =='management' or child.text =='safeguard' or child.text =='examination'))):
                                                                               return True

"""# Extraction Rules: Member States

The following code contains a set of classification rules to categorize provisions in legal texts related to Member States. The subsections contain respectively rules to extract:
- delegating provisions,
- soft obligation provisions,
- constraining provisions.

## Member States: Delegating provisions
"""

def classify_del_ms(dict):
#### General Rule: G1
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS')
         and ((dict['pmod']==True and dict['neg']==None) # may
               or (dict['needaux']==True and dict['neg']==True) or (dict['needroot']==True and dict['needneg']==True)) # need not
         and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1'
## Derivative Rules: G1
# Passive
    if ((dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS') and dict['auxpass']==True
        and ((dict['pmod']==True and dict['neg']==None) # may
              or (dict['needaux']==True and dict['neg']==True) or (dict['needroot']==True and dict['needneg']==True)) # need not
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_pass'
# Act
    if (dict['pobj2subj']=='MS' and dict['pmod']==True and dict['neg']==None
        and dict['measure_subj']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_act'
# Act passive
    if (dict['pobj3']=='MS' and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_actpass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='MS' or dict['subjpass2']=='MS' or dict['rep_subjpass']=='MS')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
             return 'DP1'
# Passive
    if (dict['pobj']=='MS' and dict['auxpass']==True and dict['neg']==None and dict['to']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
# Active
    if ((dict['dobj']=='MS' or dict['dobj2']=='MS') and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P1_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='MS' or dict['subjpass2']=='MS' or dict['rep_subjpass']=='MS')
        and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Active
    if ((dict['dobj']=='MS' or dict['dobj2']=='MS') and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_dobj'
# Act or Right
    if (dict['pobj2dobj']=='MS' and dict['neg']==True
        and (dict['measure_dobj']==True or dict['right_dobj']==True)
        and dict['root']=='CONSTRAINT'):
            return 'C1_actright'
# Nothing/No-provision
    if ((dict['dobj']=='MS' or dict['dobj2']=='MS')
        and dict['neg']==None and dict['nothing']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_nothing'

#### No Effect Rule: NO_EFFECT
    if (dict['pobj5']=='MS' and dict['smod']==True and dict['neg']==None
        and dict['noeffect']==True and dict['measure_pobj2']==True
        and dict['have']==True):
            return 'NO_EFFECT'

#### Right Rule: RIGHT
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS') and dict['neg']==None and
        ((dict['free']==True and dict['be']==True) # MS are free
          or (dict['competent']==True and dict['remain']==True) # MS remain competent
          or ((dict['right_dobj']==True and (dict['retain']==True or dict['have']==True))))): # MS retain/have the right
            return 'RIGHT'

def classify_del_ms2(dict):
#### Prejudice Rule: PREJEXPR
# “without prejudice to the power(s)/right(s)/prerogative(s) of the Member States”
    if ((dict['pobj6']=='MS' or dict['pobj7']=='MS')
       and dict['prejudice']==True and dict['right']==True):
            return 'PREJEXPR1'

# “save on grounds of public policy, public security or public health”
    if (sentence.text.find("grounds") != -1 and
        sentence.text.find("public security") != -1 and
        sentence.text.find("public policy") != -1):
         return 'PREJEXPR2'

"""## Member States: Soft obligation provisions"""

def classify_so_ms(dict):
#### General Rule: G1 & G2
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS')
        and dict['pmod']==True and dict['neg']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G1'
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS')
        and dict['smod']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G2'
# Passive
    if ((dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G1_pass'
    if ((dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
        and dict['smod']==True and dict['auxpass']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G2_pass'

#### Recommend Rule: RECOMMEND
    if ((dict['subj']=='MS' or dict['subj2']=='MS') and dict['smod']==True
        and dict['neg']==None and (dict['recommendation_dobj']==True or dict['opinion_dobj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND'
# Passive
    if ((dict['agent']=='MS' or dict['agent2']=='MS') and dict['smod']==True
        and dict['auxpass']==True and dict['neg']==None
        and (dict['recommendation_subj']==True or dict['opinion_subj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND_pass'

def classify_so_ms2(dict):

#### Collaboration: COLLABORATION
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS' or
         dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
          and (sentence.text.find('in collaboration with')!=-1 or sentence.text.find('in coordination with')!=-1
          or sentence.text.find('in cooperation with')!=-1 or sentence.text.find('in close collaboration with')!=-1
          or sentence.text.find('in close coordination with')!=-1 or sentence.text.find('in close cooperation with')!=-1)):
                    return 'COLLABORATION'

"""### Member States: Constraining provisions"""

def classify_con_ms(dict):
#### General Rules: G1 & G2
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS')
        and dict['pmod']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1'
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS') and dict['smod']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2'
## Derivative Rules: G1 & G2
# Passive
    if ((dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_pass'
# Passive
    if ((dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
        and dict['smod']==True and dict['auxpass']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_pass'
# Act
    if (dict['pobj2subj']=='MS' and dict['pmod']==True and dict['neg']==True
        and dict['measure_subj']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_act'
    if (dict['pobj2subj']=='MS' and dict['smod']==True
        and dict['measure_subj']==True and dict['remain']==None and dict['force']==None
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_act'
# Act passive
    if (dict['pobj3']=='MS' and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_actpass'
    if (dict['pobj3']=='MS' and dict['smod']==True and dict['auxpass']==True
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_actpass'

#### Delegation Permission Rules
    if ((dict['subjpass']=='MS' or dict['subjpass2']=='MS' or dict['rep_subjpass']=='MS')
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
    if ((dict['subjpass']=='MS' or dict['subjpass2']=='MS' or dict['rep_subjpass']=='MS')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2'
# Passive
    if (dict['pobj']=='MS' and dict['auxpass']==True and dict['neg']==True
        and dict['to']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
# Direct object
    if ((dict['dobj']=='MS' or dict['dobj2']=='MS') and dict['pmod']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='MS'  or dict['subjpass2']=='MS' or dict['rep_subjpass']=='MS')
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='CONSTRAINT'):
            return 'C1'

#### No Effect Rule: NO_EFFECT
    if (dict['pobj4']=='MS' and dict['smod']==True and dict['neg']==None
        and dict['noeffect']==True and dict['measure_subj']==True
        and dict['have']==True):
            return 'NO_EFFECT'

def classify_con_ms2(dict):

#### Consultation: CONSULTATION
    if ((dict['subj']=='MS' or dict['subj2']=='MS' or dict['rep_subj']=='MS' or
         dict['agent']=='MS' or dict['agent2']=='MS' or dict['rep_agent']=='MS')
          and (sentence.text.find('After consulting')!=-1 or sentence.text.find('after consulting')!=-1
          or sentence.text.find('After consultation')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('in consultation')!=-1
          or sentence.text.find('After having consulted')!=-1 or sentence.text.find('after having consulted')!=-1
          or sentence.text.find('Following consultation')!=-1 or sentence.text.find('following consultation')!=-1
          or sentence.text.find('After having heard')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
                    return 'CONSULTATION'

"""# Extraction Rules: National Competent Authorities

The following code contains a set of classification rules to categorize provisions in legal texts related to National Competent Authorities. The subsections contain respectively rules to extract:
- delegating provisions,
- soft obligation provisions,
- constraining provisions.

## National Competent Authorities: Delegating provisions
"""

def classify_del_nca(dict):
#### General Rule: G1
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA')
         and ((dict['pmod']==True and dict['neg']==None) # may
               or (dict['needaux']==True and dict['neg']==True) or (dict['needroot']==True and dict['needneg']==True)) # need not
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1'
## Derivative Rules: G1
# Passive
    if ((dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA') and dict['auxpass']==True
        and ((dict['pmod']==True and dict['neg']==None) # may
              or (dict['needaux']==True and dict['neg']==True) or (dict['needroot']==True and dict['needneg']==True)) # need not
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_pass'
# Act
    if (dict['pobj2subj']=='CA' and dict['pmod']==True and dict['neg']==None
        and dict['measure_subj']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_act'
# Act passive
    if (dict['pobj3']=='CA' and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_actpass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='CA' or dict['subjpass2']=='CA' or dict['rep_subjpass']=='CA')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
# Passive
    if (dict['pobj']=='CA' and dict['auxpass']==True and dict['neg']==None and dict['to']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
    if ((dict['dobj']=='CA' or dict['dobj2']=='CA') and dict['pmod']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P1_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='CA' or dict['subjpass2']=='CA' or dict['rep_subjpass']=='CA')
        and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Passive
    if ((dict['dobj']=='CA' or dict['dobj2']=='CA') and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_dobj'
# Act or Right
    if (dict['pobj2dobj']=='CA' and dict['neg']==True
        and (dict['measure_dobj']==True or dict['right_dobj']==True)
        and dict['root']=='CONSTRAINT'):
            return 'C1_actright'
# Nothing/No-provision
    if ((dict['dobj']=='CA' or dict['dobj2']=='CA')
        and dict['neg']==None and dict['nothing']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_nothing'

### No Effect Rule: NO EFFECT
    if (dict['pobj5']=='CA' and dict['smod']==True and dict['neg']==None
        and dict['noeffect']==True and dict['measure_pobj2']==True
        and dict['have']==True):
            return 'NO_EFFECT'

#### Right Rule: RIGHT
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA') and dict['neg']==None and
        ((dict['free']==True and dict['be']==True) # CA are free
          or (dict['competent']==True and dict['remain']==True) # CA remain competent
          or ((dict['right_dobj']==True and (dict['retain']==True or dict['have']==True)))  # CA retain/have the right
          or (sentence.text.find('personnel')!=-1 and dict['have']==True))): # CA shall have sufficient personnel (ONLY FOR CA)
              return 'RIGHT'

def classify_del_nca2(dict):

#### Prejudice Rule: PREJEXPR
# “without prejudice to the power(s)/right(s)/prerogative(s) of the CA of the Member States”
    if ((dict['pobj6']=='CA' or dict['pobj7']=='CA')
       and dict['prejudice']==True and dict['right']==True):
            return 'PREJEXPR'

"""## National Competent Authorities: Soft obligation provisions"""

def classify_so_nca(dict):
#### General Rule: G1 & G2
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA')
        and dict['pmod']==True and dict['neg']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G1'
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA')
        and dict['smod']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G2'
# Passive
    if ((dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G1_pass'
    if ((dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
        and dict['smod']==True and dict['auxpass']==True
        and dict['root']=='SOFT_IMPL'):
                return 'G2_pass'

#### Recommend Rule: RECOMMEND
    if ((dict['subj']=='CA' or dict['subj2']=='CA') and dict['smod']==True
        and dict['neg']==None and (dict['recommendation_dobj']==True or dict['opinion_dobj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND'
# Passive
    if ((dict['agent']=='CA' or dict['agent2']=='CA') and dict['smod']==True
        and dict['auxpass']==True and dict['neg']==None
        and (dict['recommendation_subj']==True or dict['opinion_subj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND_pass'

def classify_so_nca2(dict):

#### Collaboration SC : COLLABORATION
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA' or
         dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
          and (sentence.text.find('in collaboration with')!=-1 or sentence.text.find('in coordination with')!=-1
          or sentence.text.find('in cooperation with')!=-1 or sentence.text.find('in close collaboration with')!=-1
          or sentence.text.find('in close coordination with')!=-1 or sentence.text.find('in close cooperation with')!=-1)):
                    return 'COLLABORATION'

"""### National Competent Authorities: Constraining provisions"""

def classify_con_nca(dict):
#### General Rules: G1 & G2
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA')
        and dict['pmod']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1'
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA') and dict['smod']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2'
## Derivative Rules: G1 & G2
# Passive
    if ((dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_pass'
    if ((dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
        and dict['smod']==True and dict['auxpass']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_pass'
# Act
    if (dict['pobj2subj']=='CA' and dict['pmod']==True and dict['neg']==True
        and dict['measure_subj']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_act'
    if (dict['pobj2subj']=='CA' and dict['smod']==True
        and dict['measure_subj']==True and dict['remain']==None and dict['force']==None
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_act'
# Act passive
    if (dict['pobj3']=='CA' and dict['pmod']==True and dict['auxpass']==True and dict['neg']==True
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G1_actpass'
    if (dict['pobj3']=='CA' and dict['smod']==True and dict['auxpass']==True
        and dict['measure_pobj']==True and dict['by']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT')):
                return 'G2_actpass'

#### Delegation Permission Rules: DP1 & P2
    if ((dict['subjpass']=='CA' or dict['subjpass2']=='CA' or dict['rep_subjpass']=='CA')
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
    if ((dict['subjpass']=='CA' or dict['subjpass2']=='CA' or dict['rep_subjpass']=='CA')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2'
# Passive
    if (dict['pobj']=='CA' and dict['auxpass']==True and dict['neg']==True
        and dict['to']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
# Direct object
    if ((dict['dobj']=='CA' or dict['dobj2']=='CA') and dict['pmod']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2_dobj'

#### Constraint: C1
    if ((dict['subjpass']=='CA'  or dict['subjpass2']=='CA' or dict['rep_subjpass']=='CA')
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='CONSTRAINT'):
            return 'C1'

#### No Effect Rule ND: NO_EFFECT
    if (dict['pobj4']=='CA' and dict['smod']==True and dict['neg']==None
        and dict['noeffect']==True and dict['measure_subj']==True
        and dict['have']==True):
            return 'NO_EFFECT'

#### Secrecy Rule: SECRECY (ONLY RELEVANT FOR NATIONAL COMPETENT AUTHORITIES)
    if ((dict['pobj']=='CA' or dict['pobj2']=='CA') and dict['smod']==True and dict['neg']==None
        and dict['secrecy']==True
        and dict['apply']==True):
            return 'SECRECY_pobj'

def classify_con_nca2(dict):

#### Consultation NC: CONSULTATION
    if ((dict['subj']=='CA' or dict['subj2']=='CA' or dict['rep_subj']=='CA' or
         dict['agent']=='CA' or dict['agent2']=='CA' or dict['rep_agent']=='CA')
         and (sentence.text.find('After consulting')!=-1 or sentence.text.find('after consulting')!=-1
          or sentence.text.find('After consultation')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('in consultation')!=-1
          or sentence.text.find('After having consulted')!=-1 or sentence.text.find('after having consulted')!=-1
          or sentence.text.find('Following consultation')!=-1 or sentence.text.find('following consultation')!=-1
          or sentence.text.find('After having heard')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
                    return 'CONSULTATION'

"""# Extraction Rules: European Commission

The following code contains a set of classification rules to categorize provisions in legal texts related to the European Commission. The subsections contain respectively rules to extract:
- agenda setting provisions,
- delegating provisions,
- soft implementation provisions,
- constraining provisions.

## European Commission: Agenda-setting provisions
"""

def classify_agenda(dict):
#### Propose Rule: PROPOSE
    if (dict['subj']=='COM' and (dict['pmod']==True or dict['smod']==True) and dict['neg']==None
        and (dict['propose']==True or dict['propose2']==True)): # the latter for 'whether to propose'
                return 'PROPOSE'
# Passive
    if (dict['agent']=='COM' and (dict['pmod']==True or dict['smod']==True) and dict['auxpass']==True
        and dict['neg']==None
        and dict['propose']==True):
                return 'PROPOSE_pass'

#### Submit Rule: SUBMIT
    if (dict['subj']=='COM' and (dict['pmod']==True or dict['smod']==True)
        and dict['neg']==None and dict['committee_pobj']==None # excl. submission to committees (constraint)
        and ((dict['proposal_dobj']==True and (dict['make']==True or dict['submit']==True
              or (dict['put']==True and dict['forward']==True) or dict['prepare']==True)) # 'make/submit/prepare/put forward a proposal/draft'
          or ((dict['recommendation_dobj']==True or dict['measure_dobj']==True)
               and (dict['submit']==True or (dict['put']==True and dict['forward']==True) or dict['prepare']==True)))): # 'submit/prepare/put forward a recommendation/decision/measure',
                   return 'SUBMIT' #  note: 'make a standard (-> measure)' is delegation, 'make a recommendation' is soft power

# Passive
    if (dict['agent']=='COM' and (dict['pmod']==True or dict['smod']==True) and dict['auxpass']==True and dict['neg']==None
        and ((dict['proposal_subj']==True and (dict['make']==True or dict['submit']==True
                or (dict['put']==True and dict['forward']==True) or dict['prepare']==True)) # 'a proposal shall be made/submitted/prepared/put forward'
             or ((dict['recommendation_subj']==True or dict['measure_subj']==True)
             and (dict['submit']==True or (dict['put']==True and dict['forward']==True) or dict['prepare']==True)))): # 'a recommendation/decision shall be submitted/prepared/put forward'
                  return 'SUBMIT_pass'

#### Proposal Expressions: PROPOSAL
# “(acting) on a proposal from the Commission”, “on a proposal of the Commission”, “on a Commission proposal”
# “(acting) on the basis of a proposal of the Commission”, “on the basis of a Commission proposal”
    if ((dict['pobj3']=='COM' or dict['pobj5']=='COM'or dict['pobj6']=='COM' or dict['pobj7']=='COM' or dict['compound']=='COM')
         and dict['proposal']==True
         and (sentence.text.find("On the") != -1 or sentence.text.find("On a") != -1 or sentence.text.find("Upon the") != -1
          or sentence.text.find("on the") != -1 or sentence.text.find("on a") != -1 or sentence.text.find("upon the") != -1
          or sentence.text.find("submission by the Commission") != -1)):
                return 'PROPOSAL1'
# “accompanied … by a legislative proposal”
    if ((dict['by']==True or dict['by2']==True or dict['by3']==True) and dict['legprop']==True):
                return 'PROPOSAL2'
    if (sentence.text.find("by a legislative proposal") != -1 or sentence.text.find("by legislative proposals") != -1):
                return 'PROPOSAL3'

"""## European Commission: Delegating provisions"""

def classify_del_com(dict):
#### General Rule: G1
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM') and dict['neg']==None
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or (dict['pmod']==True and dict['root']=='ACTIVE_CONSTRAINT'))):
                  return 'G1'
## Derivative Rules: G1
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or (dict['pmod']==True and dict['root']=='ACTIVE_CONSTRAINT'))):
                return 'G1_pass'
# Act
    if ((dict['pobj2subj']=='COM' or dict['compound']=='COM' or (dict['pobj4']=='COM' and dict['by2']==True)) #  e.g. Measures of the Commission (Commission measures / decided upon by the Commission) may set
        and dict['pmod']==True and dict['auxpass']==None and dict['neg']==None
        and dict['measure_subj']==True and sentence.text.find("to the Commission") == -1 # To exclude false positives
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT')):
                return 'G1_act'
# Act Passive
    if ((dict['pobj3']=='COM' or dict['compound']=='COM' or (dict['pobj5']=='COM' and dict['by3']==True))
          and dict['auxpass']==True and dict['neg']==None and dict['measure_pobj']==True and dict['by']==True
          and sentence.text.find("to the Commission") == -1 # To exclude false positives
          and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT')):
                return 'G1_actpass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='COM' or dict['subjpass2']=='COM' or dict['rep_subjpass']=='COM')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
# Passive
    if ((dict['pobj']=='COM' or dict['compound_subj']=='COM') # compound: 'to the Commission subject'
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='DELEGATION'):
                return 'D1_pobj'
# Active
    if ((dict['dobj']=='COM' or dict['dobj2']=='COM') and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P1_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='COM' or dict['subjpass2']=='COM' or dict['rep_subjpass']=='COM')
        and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Passive
    if ((dict['dobj']=='COM' or dict['dobj2']=='COM') and dict['neg']==True
            and dict['root']=='CONSTRAINT'):
                return 'C1_dobj'
# Act or Right
    if ((dict['pobj2dobj']=='COM' or dict['pobj4']=='COM') and dict['neg']==True and
        (dict['right_dobj']==True or dict['measure_dobj']==True)
        and dict['root']=='CONSTRAINT'):
            return 'C1_actright'
# Act
    if (dict['pobj2dobj']=='COM' and dict['smod']==True and dict['neg']==None and dict['measure_dobj']==True
            and dict['root']=='CONSTRAINT'):
                return 'C1_act'

"""## European Commission: Soft implementation provisions"""

def classify_si_com(dict):
#### General Rule: G1
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM')
        and (dict['pmod']==True or dict['smod']==True) and dict['neg']==None
        and (dict['root']=='SOFT_IMPL' or dict['provide']==True)):
                return 'G1'
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
        and (dict['pmod']==True or dict['smod']==True) and dict['auxpass']==True
        and dict['neg']==None
        and (dict['root']=='SOFT_IMPL' or dict['provide']==True)):
                return 'G1_pass'

#### Recommend Rule: RECOMMEND
    if ((dict['subj']=='COM' or dict['subj2']=='COM') and (dict['pmod']==True or dict['smod']==True)
        and dict['neg']==None and (dict['recommendation_dobj']==True or dict['opinion_dobj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND'
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM') and (dict['pmod']==True or dict['smod']==True)
        and dict['auxpass']==True and dict['neg']==None
        and (dict['recommendation_subj']==True or dict['opinion_subj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND_pass'

def classify_si_com2(dict):

#### Collaboration: COLLABORATION
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM' or
         dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
          and (sentence.text.find('in collaboration with')!=-1 or sentence.text.find('in coordination with')!=-1
          or sentence.text.find('in cooperation with')!=-1 or sentence.text.find('in close collaboration with')!=-1
          or sentence.text.find('in close coordination with')!=-1 or sentence.text.find('in close cooperation with')!=-1)):
                    return 'COLLABORATION'

"""## European Commission: Constraining provisions"""

def classify_con_com(dict):
#### General Rule: G1
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM') and (dict['pmod']==True or dict['smod']==True)
        and dict['neg']==True and dict['responsible']==None # excl. "The Commission shall not be responsible"
        and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1'
## Derivative Rules: G1
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM') and (dict['pmod']==True or dict['smod']==True)
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_pass'
# Act
    if (((dict['pobj2subj']=='COM' or dict['compound']=='COM' or (dict['pobj4']=='COM' and dict['by2']==True))
          and dict['pmod']==True and dict['neg']==True
          and (dict['measure_subj']==True or dict['recommendation_subj']==True or dict['opinion_subj']==True)
          and dict['to2']==None # excl. "Application to the Commission may not..."
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL'))):
                return 'G1_act_p'

    if ((dict['pobj2subj']=='COM' or dict['compound']=='COM' or (dict['pobj4']=='COM' and dict['by2']==True))
          and dict['smod']==True
          and (dict['measure_subj']==True or dict['recommendation_subj']==True or dict['opinion_subj']==True)
          and dict['to2']==None # excl. "Application to the Commission shall..."
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_act_s'
# Act Passive
    if ((dict['pobj3']=='COM' or dict['compound']=='COM' or (dict['pobj5']=='COM' and dict['by3']==True))
          and dict['auxpass']==True and dict['neg']==True and dict['by']==True
          and (dict['measure_pobj']==True or dict['recommendation_pobj']==True or dict['opinion_pobj']==True)
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                  return 'G1_act_pass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='COM' or dict['subjpass2']=='COM' or dict['rep_subjpass']=='COM')
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
    if ((dict['subjpass']=='COM' or dict['subjpass2']=='COM' or dict['rep_subjpass']=='COM')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2'
# Passive
    if (dict['pobj']=='COM' and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
# Active
    if ((dict['dobj']=='COM' or dict['dobj2']=='COM') and dict['pmod']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='COM' or dict['subjpass2']=='COM' or dict['rep_subjpass']=='COM')
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Opinion
    if (dict['subj']=='COM' and dict['smod']==True and dict['neg']==None and dict['opinion_dobj']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_opinion'

#### Information Rule: INFORMATION
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM')
        and dict['smod']==True and dict['neg']==None
        and dict['information_dobjpobj']==True
        and (dict['draw']==True or dict['enter']==True or dict['give']==True
        or  dict['take']==True or dict['submit']==True or dict['prepare']==True
        or  dict['provide']==True)):
            return 'INFORMATION'
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
        and dict['smod']==True and dict['auxpass']==True
        and dict['neg']==None and dict['information_subj']==True
        and (dict['draw']==True or dict['enter']==True or dict['give']==True
        or  dict['take']==True or dict['submit']==True or dict['prepare']==True
        or  dict['provide']==True)):
            return 'INFORMATION_pobj'

#### Public Rule: PUBLIC
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM')
        and dict['smod']==True and dict['neg']==None
        and dict['public']==True
        and dict['make']==True):
             return 'PUBLIC'
# Passive
    if ((dict['pobj']=='COM' or dict['pobj4']=='COM') and dict['smod']==True and dict['auxpass']==True # made public/available by the Commission
        and dict['neg']==None and (dict['by']==True or dict['by2']==True) and dict['public']==True  # Information received by the Commission shall be made public
        and dict['make']==True):
             return 'PUBLIC_pobj'

#### Refer Rule: REFER
    if ((dict['pobj2']=='COM' or dict['compound']=='COM' or dict['pobj4']=='COM') and dict['pmod']==True
         and dict['neg']==None and (dict['measure_subj']==True or dict['measure_dobj']==True)
        and dict['refer']==True):
            return 'REFER'

#### Active Constraint Rule: AC1 (it should be after INFORMATION because of the overlap with SUBMIT)
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM')
        and dict['smod']==True and dict['neg']==None
        and dict['root']=='ACTIVE_CONSTRAINT'):
            return 'AC1'
# Passive
    if ((dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
        and dict['auxpass']==True and dict['smod']==True and dict['neg']==None
         and dict['root']=='ACTIVE_CONSTRAINT'):
            return 'AC1_pobj'

#### Comitology Expressions: COMIT  (ONLY RELEVANT FOR THE COMMISSION)
## Period 1958-1987: see rules AC1 and AC1_pobj ('submit' is an ACTIVE_CONSTRAINT)
## Period 1988-1999: COMIT88-99
# Variant a
    if ((dict['subjpass']=='COM' or dict['dobj']=='COM') # "The Commission shall be assisted by a committee"
         and (dict['committee_agent']==True or dict['committee_subj']==True) # "The committee shall assist the Commission"
         and dict['smod']==True and dict['neg']==None
         and dict['assist']==True):
                return 'COMIT88-99a'
# Variant b
    if ((dict['subj']=='COM' or dict['subjpass']=='COM' or dict['agent']=='COM') and dict['smod']==True
          and dict['neg']==None and sentence.text.find('assisted')!=-1
          and dict['committee']==True and (dict['by2']==True or dict['by3']==True)): # "The Commission, assisted by a committee, shall [be]"
                return 'COMIT88-99b' # "...by the Commission assisted by a committee"
## Period 2000-2022: COMIT00-22
# Variant a
    if (dict['subj']=='COM' and dict['neg']==None
          and dict['accordance']==True and dict['comitproc']==True): # e.g. "The Commission shall/may adopt the decision in accordance with the ... procedure"
                return 'COMIT00-22a'
# Variant b
    if (dict['auxpass']==True and dict['neg']==None
          and dict['accordance']==True and dict['comitproc']==True): # e.g. "... shall/may be decided in accordance with the ... procedure"
                return 'COMIT00-22b'
## Period 2000-2009: COMIT00-09
# Variant a
    if ((dict['subj']=='COM' or dict['subjpass']=='COM' or dict['agent']=='COM' ) and
             (sentence.text.find('subject to the advisory procedure') != -1
          or sentence.text.find('subject to the management procedure') != -1
          or sentence.text.find('subject to the regulatory procedure') != -1
          or sentence.text.find('subject to the safeguard procedure') != -1
          or sentence.text.find('subject to the examination procedure') != -1)): # COMIT10-22
                return 'COMIT00-09'
## Period 2010-2022: COMIT10-22
# Variant a
    if ((dict['pobj']=='COM' or dict['compound_subj']=='COM') and dict['auxpass']==True # compound_subj: to the Commission subject to
          and dict['neg']==None and dict['right_subj']==True and dict['teract']==True
          and (sentence.text.find('subject to') != -1 or dict['accordance']==True)
          and dict['root']=='DELEGATION'):
                return 'COMIT10-22a'
# Variant b
    if ((dict['subj']=='COM' or dict['subjpass']=='COM') and dict['smod']==True and dict['neg']==None
          and dict['teract']==True and dict['accordance']==True
          and (dict['adopt']==True or dict['root']=='DELEGATION')): # e.g. "The Commission shall adopt implementing acts in accordance with"
                return 'COMIT10-22b'
# Variant c
    if (dict['teract']==True and dict['smod']==True and dict['auxpass']==True
          and dict['neg']==None and dict['accordance']==True
          and dict['adopt']==True): # e.g. "implementing acts shall be adopted in accordance with"
                return 'COMIT10-22c'

def classify_con_com2(dict):

#### Consultation: CONSULTATION
    if ((dict['subj']=='COM' or dict['subj2']=='COM' or dict['rep_subj']=='COM' or
         dict['agent']=='COM' or dict['agent2']=='COM' or dict['rep_agent']=='COM')
        and (sentence.text.find('After consulting')!=-1 or sentence.text.find('After consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('After having heard')!=-1
          or sentence.text.find('after consulting')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('following consultation')!=-1 or sentence.text.find('Following consultation')!=-1
          or sentence.text.find('in consultation')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
                    return 'CONSULTATION'
# Act
    if (((dict['pobj3']=='COM' or dict['pobj5']=='COM' or dict['compound']=='COM')
          and dict['auxpass']==True and dict['neg']==None and dict['measure_pobj']==True and (dict['by']==True or dict['by3']==True)
          and sentence.text.find("to the Commission") == -1 ) # To exclude false positives
          and (sentence.text.find('After consulting')!=-1 or sentence.text.find('After consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('After having heard')!=-1
          or sentence.text.find('after consulting')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('following consultation')!=-1 or sentence.text.find('Following consultation')!=-1
          or sentence.text.find('in consultation')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
                    return 'CONSULTATION_act'

"""# Extraction Rules: Supranational Agencies
The following code contains a set of classification rules to categorize provisions in legal texts related to Supranational Agenciess. The subsections contain respectively rules to extract:
- delegating provisions,
- soft implementation provisions,
- constraining provisions.

## Supranational Agencies: Delegating provisions
"""

def classify_del_age(dict):
#### General Rule: G1
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE')
        and dict['neg']==None
        and dict['board_dobj']==None and sentence.text.find("shall comprise")==-1 # excl. organizational features
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or (dict['pmod']==True and dict['root']=='ACTIVE_CONSTRAINT'))):
                return 'G1'

## Derivative Rules: G1
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or (dict['pmod']==True and dict['root']=='ACTIVE_CONSTRAINT'))):
                return 'G1_pass'
# Act
    if ((dict['pobj2subj']=='AGE' or dict['compound']=='AGE' or (dict['pobj4']=='AGE' and dict['by2']==True)) #  e.g. Measures of the Agency (Agency measures / decided upon by the Agency) may set
        and dict['pmod']==True and dict['auxpass']==None and dict['neg']==None
        and dict['measure_subj']==True
        and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT')):
                return 'G1_act'
# Act Passive
    if ((dict['pobj3']=='AGE' or dict['compound']=='AGE' or (dict['pobj5']=='AGE' and dict['by3']==True))
          and dict['auxpass']==True and dict['neg']==None and dict['measure_pobj']==True and dict['by']==True
          and (dict['root']==None or dict['root']=='DELEGATION'
             or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT')):
                return 'G1_actpass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='AGE' or dict['subjpass2']=='AGE' or dict['rep_subjpass']=='AGE')
        and dict['auxpass']==True and dict['neg']==None
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
# Passive
    if ((dict['pobj']=='AGE' or dict['compound_subj']=='AGE') # compound: 'to the Agency subject'
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='DELEGATION'):
                return 'D1_pobj'
# Active
    if ((dict['dobj']=='AGE' or dict['dobj2']=='AGE') and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P1_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='AGE' or dict['subjpass2']=='AGE' or dict['rep_subjpass']=='AGE')
        and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Passive
    if ((dict['dobj']=='AGE' or dict['dobj2']=='AGE') and dict['neg']==True
            and dict['root']=='CONSTRAINT'):
                return 'C1_dobj'
# Act or Right
    if ((dict['pobj2dobj']=='AGE' or dict['pobj4']=='AGE') and dict['neg']==True and
        (dict['right_dobj']==True or dict['measure_dobj']==True)
        and dict['root']=='CONSTRAINT'):
            return 'C1_actright'
# Act
    if (dict['pobj2dobj']=='AGE' and dict['smod']==True and dict['neg']==None and dict['measure_dobj']==True
            and dict['root']=='CONSTRAINT'):
                return 'C1_act'

"""## Supranational Agencies: Soft implementation provisions"""

def classify_si_age(dict):
#### General Rule: G1
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE')
        and (dict['pmod']==True or dict['smod']==True) and dict['neg']==None
        and (dict['root']=='SOFT_IMPL' or dict['provide']==True)):
                return 'G1'
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
        and (dict['pmod']==True or dict['smod']==True) and dict['auxpass']==True
        and dict['neg']==None
        and (dict['root']=='SOFT_IMPL' or dict['provide']==True)):
                return 'G1_pass'

#### Recommend Rule: RECOMMEND
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE') and (dict['pmod']==True or dict['smod']==True)
        and dict['neg']==None and (dict['recommendation_dobj']==True or dict['opinion_dobj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND'
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE') and (dict['pmod']==True or dict['smod']==True)
        and dict['auxpass']==True and dict['neg']==None
        and (dict['recommendation_subj']==True or dict['opinion_subj']==True)
        and (dict['adopt']==True or dict['issueroot']==True or dict['make']==True)):
                return 'RECOMMEND_pass'

def classify_si_age2(dict):

#### Collaboration: COLLABORATION
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE' or
         dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
          and (sentence.text.find('in collaboration with')!=-1 or sentence.text.find('in coordination with')!=-1
          or sentence.text.find('in cooperation with')!=-1 or sentence.text.find('in close collaboration with')!=-1
          or sentence.text.find('in close coordination with')!=-1 or sentence.text.find('in close cooperation with')!=-1)):
                    return 'COLLABORATION'

"""## Supranational Agencies: Constraining provisions"""

def classify_con_age(dict):
#### General Rule: G1
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE') and (dict['pmod']==True or dict['smod']==True)
        and dict['neg']==True and dict['responsible']==None # excl. "The Agency shall not be responsible"
        and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1'

## Derivative Rules: G1
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE') and (dict['pmod']==True or dict['smod']==True)
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
             or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_pass'

# Act
    if (((dict['pobj2subj']=='AGE' or (dict['pobj4']=='AGE' and dict['by2']==True)) # dict['compound']=='AGE' produces false positive
          and dict['pmod']==True and dict['neg']==True
          and (dict['measure_subj']==True or dict['recommendation_subj']==True or dict['opinion_subj']==True)
          and dict['to2']==None # excl. "Application to the Agency may not..."
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL'))):
                return 'G1_act_p'

    if ((dict['pobj2subj']=='AGE' or (dict['pobj4']=='AGE' and dict['by2']==True)) # dict['compound']=='AGE' produces false positive
          and dict['smod']==True
          and (dict['measure_subj']==True or dict['recommendation_subj']==True or dict['opinion_subj']==True)
          and dict['to2']==None # excl. "Application to the Commission shall..."
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                return 'G1_act_s'

# Act Passive
    if ((dict['pobj3']=='AGE' or dict['compound']=='AGE' or (dict['pobj5']=='AGE' and dict['by3']==True))
          and dict['auxpass']==True and dict['neg']==True and dict['by']==True
          and (dict['measure_pobj']==True or dict['recommendation_pobj']==True or dict['opinion_pobj']==True)
          and (dict['root']==None or dict['root']=='DELEGATION' or dict['root']=='PERMISSION' or dict['root']=='CONSTRAINT'
               or dict['root']=='ACTIVE_CONSTRAINT' or dict['root']=='SOFT_IMPL')):
                  return 'G1_act_pass'

#### Delegation Permission Rule: DP1
    if ((dict['subjpass']=='AGE' or dict['subjpass2']=='AGE' or dict['rep_subjpass']=='AGE')
        and dict['auxpass']==True and dict['neg']==True
        and (dict['root']=='DELEGATION' or dict['root']=='PERMISSION')):
            return 'DP1'
    if ((dict['subjpass']=='AGE' or dict['subjpass2']=='AGE'  or dict['rep_subjpass']=='AGE')
        and dict['pmod']==True and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2'
# Passive
    if (dict['pobj']=='AGE' and dict['auxpass']==True and dict['neg']==True
        and dict['root']=='DELEGATION'):
            return 'D1_pobj'
# Active
    if ((dict['dobj']=='AGE' or dict['dobj2']=='AGE') and dict['pmod']==True and dict['neg']==None
        and dict['root']=='PERMISSION'):
            return 'P2_dobj'

#### Constraint Rule: C1
    if ((dict['subjpass']=='AGE' or dict['subjpass2']=='AGE' or dict['rep_subjpass']=='AGE')
        and dict['auxpass']==True and dict['neg']==None
        and dict['root']=='CONSTRAINT'):
            return 'C1'
# Opinion
    if (dict['subj']=='AGE' and dict['smod']==True and dict['neg']==None and dict['opinion_dobj']==True
        and dict['root']=='CONSTRAINT'):
            return 'C1_opinion'

#### Active Constraint Rule: AC1
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE')
        and (dict['smod']==True or dict['pmod']==None) and dict['neg']==None # strict modal or indicative
        and (dict['root']=='ACTIVE_CONSTRAINT' or (dict['accountable']==True and dict['be']==True))):
            return 'AC1'
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
        and dict['smod']==True and dict['auxpass']==True and dict['neg']==None
         and dict['root']=='ACTIVE_CONSTRAINT'):
            return 'AC1_pobj'

#### Information Rule: INFORMATION
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE')
        and dict['smod']==True and dict['neg']==None
        and dict['information_dobjpobj']==True
        and (dict['draw']==True or dict['enter']==True or dict['give']==True
        or  dict['take']==True or dict['submit']==True or dict['prepare']==True
        or  dict['provide']==True)):
            return 'INFORMATION'
# Passive
    if ((dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
        and dict['smod']==True and dict['auxpass']==True
        and dict['neg']==None and dict['information_subj']==True
        and (dict['draw']==True or dict['enter']==True or dict['give']==True
        or  dict['take']==True or dict['submit']==True or dict['prepare']==True
        or  dict['provide']==True)):
            return 'INFORMATION_pobj'

#### Public Rule: PUBLIC
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE')
        and dict['smod']==True and dict['neg']==None
        and (dict['public']==True or dict['good']==True)
        and dict['make']==True):
             return 'PUBLIC'
# Passive
    if ((dict['pobj']=='AGE' or dict['pobj4']=='AGE') and dict['smod']==True and dict['auxpass']==True # made public/available by the Agency
        and dict['neg']==None and (dict['by']==True or dict['by2']==True) and dict['public']==True  # Information received by the Agency shall be made public
        and dict['make']==True):
             return 'PUBLIC_pobj'

#### Refer Rule: REFER
    if ((dict['pobj2']=='AGE' or dict['compound']=='AGE' or dict['pobj4']=='AGE') and dict['pmod']==True
         and dict['neg']==None and (dict['measure_subj']==True or dict['measure_dobj']==True)
        and dict['refer']==True):
            return 'REFER'

#### Secrecy Rule: SECRECY (ONLY RELEVANT FOR SUPRANATIONAL AGENCIES)
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE') and dict['smod']==True and dict['neg']==None
        and dict['secrecy']==True
        and (dict['apply']==True)):
            return 'SECRECY'
# Passive
    if ((dict['pobj']=='AGE' or dict['pobj2']=='AGE') and dict['smod']==True and dict['neg']==None
        and dict['secrecy']==True
        and dict['apply']==True):
            return 'SECRECY_pobj'

def classify_con_age2(dict):

#### Consultation: CONSULTATION
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE' or
         dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
        and (sentence.text.find('After consulting')!=-1 or sentence.text.find('after consulting')!=-1
          or sentence.text.find('After consultation')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('in consultation')!=-1
          or sentence.text.find('After having consulted')!=-1 or sentence.text.find('after having consulted')!=-1
          or sentence.text.find('Following consultation')!=-1 or sentence.text.find('following consultation')!=-1
          or sentence.text.find('After having heard')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
                    return 'CONSULTATION'
# Act
    if (((dict['pobj3']=='AGE' or dict['pobj5']=='AGE' or dict['compound']=='AGE')
          and dict['auxpass']==True and dict['neg']==None and dict['measure_pobj']==True and (dict['by']==True or dict['by3']==True))
        and (sentence.text.find('After consulting')!=-1 or sentence.text.find('after consulting')!=-1
          or sentence.text.find('After consultation')!=-1 or sentence.text.find('after consultation')!=-1
          or sentence.text.find('In consultation')!=-1 or sentence.text.find('in consultation')!=-1
          or sentence.text.find('After having consulted')!=-1 or sentence.text.find('after having consulted')!=-1
          or sentence.text.find('Following consultation')!=-1 or sentence.text.find('following consultation')!=-1
          or sentence.text.find('After having heard')!=-1 or sentence.text.find('after having heard')!=-1
          or sentence.text.find('with the agreement of')!=-1 or sentence.text.find('in agreement with')!=-1)):
               return 'CONSULTATION_act'

#### Accordance: ACCORDANCE (ONLY RELEVANT FOR SUPRANATIONAL AGENCIES)
    if ((dict['subj']=='AGE' or dict['subj2']=='AGE' or dict['rep_subj']=='AGE' or
         dict['agent']=='AGE' or dict['agent2']=='AGE' or dict['rep_agent']=='AGE')
         and dict['neg']==None
         and (sentence.text.find('subject to') != -1 or dict['accordance']==True)):
                return 'ACCORDANCE'



# ============================================================
# --- Load main English model and custom NER component ---
# ============================================================
print("\n=== Initializing pipeline ===")

nlp = spacy.load("en_core_web_lg", exclude=["ner"])
print("Base SpaCy components:", nlp.pipe_names)

ner_path = BASE_DIR / "models_files" / "NER_institutions" / "model-last"
ner = spacy.load(ner_path)
ner.replace_listeners("tok2vec", "ner", ["model.tok2vec"])
nlp.add_pipe("ner", name="ner", source=ner)
print("Added institutional NER:", nlp.pipe_names)

# ============================================================
# --- Add matchers ---
# ============================================================
@Language.component("soft_impl_matcher")
def soft_impl_matcher(doc):
    def soft_impl_ent(matcher, doc, i, matches):
        match_id, start, end = matches[i]
        entity = Span(doc, start, end, label="SOFT_IMPL")
        doc.ents += (entity,)

    patterns = [
        [{"POS": "VERB", "DEP": "ROOT", "LOWER": {"FUZZY1": "advise"}}],
        [{"POS": "VERB", "DEP": "ROOT", "LOWER": {"FUZZY1": "cooperate"}}],
        [{"POS": "VERB", "DEP": "ROOT", "LOWER": {"FUZZY1": "coordinate"}}],
        [{"POS": "VERB", "DEP": "ROOT", "LOWER": "work"}],
    ]
    matcher = Matcher(doc.vocab)
    for p in patterns:
        matcher.add("soft_impl", [p], on_match=soft_impl_ent)
    matcher(doc)
    return doc

nlp.add_pipe("soft_impl_matcher", before="ner")
print("Pipeline ready:", nlp.pipe_names)

# ============================================================
# --- Extend Doc attributes ---
# ============================================================
Doc.set_extension("celex", default=None, force=True)
Doc.set_extension("sentence_id", default=None, force=True)
Doc.set_extension("sub_sentence_id", default=None, force=True)
Doc.set_extension("length_sentence", default=None, force=True)
Doc.set_extension("length_celex", default=None, force=True)
nlp.max_length = 1_500_000

print("Doc extensions set.\n")

# ============================================================
# --- Annotation and export ---
# ============================================================
start = timeit.default_timer()

source_file = BASE_DIR / "corpus_files" / "EurLex_sentences.jsonl"
destination_file = BASE_DIR / "output_files" / "EURLEX_corpus_annotated.jsonl"
output_file = BASE_DIR / "output_files" / "EURLEX_corpus_annotated.csv"

cols = [
    "celex", "sentence_id", "sub_sentence_id", "subsub_sentence_id", "subsub_sentence_n",
    "length", "length_sentence", "length_celex",
    "text", "root", "neg", "pmod", "smod",
    "del_ms", "del_ms2", "con_ms", "con_ms2", "so_ms", "so_ms2",
    "del_nca", "del_nca2", "con_nca", "con_nca2", "so_nca", "so_nca2",
    "agenda", "del_com", "si_com", "si_com2", "con_com", "con_com2",
    "del_age", "si_age", "si_age2", "con_age", "con_age2",
    "subj", "subjpass", "subj2", "subjpass2", "dobj", "dobj2", "agent", "agent2",
    "pobj", "pobj2", "pobj3", "pobj4", "pobj5", "pobj6", "pobj7",
    "compound", "compound_subj"
]

with open(source_file, "r", encoding="utf-8") as k:
    my_list = [json.loads(line) for line in k]

with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(cols)

    with open(destination_file, "w", encoding="utf-8") as f_jsonl:

        for k, item in enumerate(my_list):
            data = {
                "celex": item["metadata"]["CELEX_number"],
                "sentence_id": item["metadata"]["sentence_id"],
                "sub_sentence_id": item["metadata"]["sub_sentence_id"],
                "length_sentence": item["metadata"]["length_sentence"],
                "length_celex": item["metadata"]["length_celex"],
                "text": item["text"],
            }

            whole_doc = nlp(data["text"])
            whole_doc._.celex = data["celex"]
            whole_doc._.sentence_id = data["sentence_id"]
            whole_doc._.sub_sentence_id = data["sub_sentence_id"]
            whole_doc._.length_sentence = data["length_sentence"]
            whole_doc._.length_celex = data["length_celex"]

            for input_sent in whole_doc.sents:
                chunks = segment_sentence_into_chunks(input_sent)
                for i, chunk in enumerate(chunks):
                    doc = nlp(chunk)
                    sentences = list(doc.sents)

                    for sentence in sentences:
                        celex = whole_doc._.celex
                        sentence_id = whole_doc._.sentence_id
                        sub_sentence_id = whole_doc._.sub_sentence_id
                        subsub_sentence_n = i
                        subsub_sentence_id = f"{sub_sentence_id}_{subsub_sentence_n}"
                        text = sentence.text
                        length = len(text)
                        length_sentence = whole_doc._.length_sentence
                        length_celex = whole_doc._.length_celex

                        # -------------------- EXTRACTION --------------------
                        subj = find_subj(extract_root(sentence))
                        subjpass = find_subjpass(extract_root(sentence))
                        subj2 = find_subj2(extract_root(sentence))
                        subjpass2 = find_subjpass2(extract_root(sentence))
                        dobj = find_dobj(extract_root(sentence))
                        dobj2 = find_dobj2(extract_root(sentence))
                        agent = find_agent(extract_root(sentence))
                        agent2 = find_agent2(extract_root(sentence))
                        pobj = find_pobj(extract_root(sentence))
                        pobj2 = find_pobj2(extract_root(sentence))
                        pobj2subj = find_pobj2subj(extract_root(sentence))
                        pobj2dobj = find_pobj2dobj(extract_root(sentence))
                        pobj3 = find_pobj3(extract_root(sentence))
                        pobj4 = find_pobj4(extract_root(sentence))
                        pobj5 = find_pobj5(extract_root(sentence))
                        pobj6 = find_pobj6(extract_root(sentence))
                        pobj7 = find_pobj7(extract_root(sentence))
                        compound = find_compound(extract_root(sentence))
                        compound_subj = find_compound_subj(extract_root(sentence))
                        board_dobj = find_board_dobj(extract_root(sentence))
                        committee = find_committee(extract_root(sentence))
                        committee_subj = find_committee_subj(extract_root(sentence))
                        committee_agent = find_committee_agent(extract_root(sentence))
                        committee_pobj = find_committee_pobj(extract_root(sentence))
                        rep = find_rep(extract_root(sentence))
                        rep_subj = find_rep_subj(extract_root(sentence))
                        rep_subjpass = find_rep_subjpass(extract_root(sentence))
                        rep_agent = find_rep_agent(extract_root(sentence))
                        nothing = find_nothing(extract_root(sentence))
                        root = find_root(sentence)
                        aux = find_aux(extract_root(sentence))
                        auxpass = find_auxpass(extract_root(sentence))
                        pmod = find_pmod(extract_root(sentence))
                        smod = find_smod(extract_root(sentence))
                        needaux = find_needaux(extract_root(sentence))
                        needroot = find_needroot(sentence)
                        needneg = find_needneg(extract_root(sentence))
                        be = find_be(sentence)
                        have = find_have(sentence)
                        give = find_give(sentence)
                        take = find_take(sentence)
                        make = find_make(sentence)
                        assist = find_assist(sentence)
                        draw = find_draw(sentence)
                        enter = find_enter(sentence)
                        prepare = find_prepare(sentence)
                        provide = find_provide(sentence)
                        propose = find_propose(sentence)
                        propose2 = find_propose2(extract_root(sentence))
                        put = find_put(sentence)
                        forward = find_forward(extract_root(sentence))
                        refer = find_refer(sentence)
                        submit = find_submit(sentence)
                        adopt = find_adopt(sentence)
                        affect = find_affect(sentence)
                        apply = find_apply(sentence)
                        issueroot = find_issueroot(sentence)
                        remain = find_remain(sentence)
                        retain = find_retain(sentence)
                        neg = find_neg(extract_root(sentence))
                        by = find_by(extract_root(sentence))
                        by2 = find_by2(extract_root(sentence))
                        by3 = find_by3(extract_root(sentence))
                        to = find_to(extract_root(sentence))
                        to2 = find_to2(extract_root(sentence))
                        competent = find_competent(extract_root(sentence))
                        force = find_force(extract_root(sentence))
                        free = find_free(extract_root(sentence))
                        noeffect = find_noeffect(extract_root(sentence))
                        prejudice = find_prejudice(extract_root(sentence))
                        accountable = find_accountable(extract_root(sentence))
                        responsible = find_responsible(extract_root(sentence))
                        right = find_right(extract_root(sentence))
                        right_subj = find_right_subj(extract_root(sentence))
                        right_dobj = find_right_dobj(extract_root(sentence))
                        proposal = find_proposal(extract_root(sentence))
                        proposal_subj = find_proposal_subj(extract_root(sentence))
                        proposal_dobj = find_proposal_dobj(extract_root(sentence))
                        legprop = find_legprop(extract_root(sentence))
                        recommendation = find_recommendation(extract_root(sentence))
                        recommendation_subj = find_recommendation_subj(extract_root(sentence))
                        recommendation_dobj = find_recommendation_dobj(extract_root(sentence))
                        recommendation_pobj = find_recommendation_pobj(extract_root(sentence))
                        opinion = find_opinion(extract_root(sentence))
                        opinion_subj = find_opinion_subj(extract_root(sentence))
                        opinion_dobj = find_opinion_dobj(extract_root(sentence))
                        opinion_pobj = find_opinion_pobj(extract_root(sentence))
                        measure = find_measure(extract_root(sentence))
                        measure_subj = find_measure_subj(extract_root(sentence))
                        measure_dobj = find_measure_dobj(extract_root(sentence))
                        measure_pobj = find_measure_pobj(extract_root(sentence))
                        measure_pobj2 = find_measure_pobj2(extract_root(sentence))
                        teract = find_teract(extract_root(sentence))
                        secrecy = find_secrecy(extract_root(sentence))
                        issue = find_issue(extract_root(sentence))
                        information = find_information(extract_root(sentence))
                        information_subj = find_information_subj(extract_root(sentence))
                        information_dobjpobj = find_information_dobjpobj(extract_root(sentence))
                        public = find_public(extract_root(sentence))
                        good = find_good(extract_root(sentence))
                        accordance = find_accordance(extract_root(sentence))
                        procedure = find_procedure(extract_root(sentence))
                        comitproc = find_comitproc(extract_root(sentence))

                        # -------------------- SENT_DICT --------------------
                        sent_dict = {'text':text,
                              # Actor labels from NER model
                              'subj':subj,'subjpass':subjpass,'subj2':subj2,'subjpass2':subjpass2,'dobj':dobj,'dobj2':dobj2,'agent':agent,'agent2':agent2,
                              'pobj':pobj,'pobj2':pobj2,'pobj2subj':pobj2subj,'pobj2dobj':pobj2dobj,'pobj3':pobj3,'pobj4':pobj4,'pobj5':pobj5,'pobj6':pobj6,
                              'pobj7':pobj7,'compound':compound,'compound_subj':compound_subj,
                              # Other generic actors and 'nothing' as subject
                              'board_dobj':board_dobj,'committee':committee,'committee_subj':committee_subj,'committee_agent':committee_agent,'committee_pobj':committee_pobj,
                              'rep':rep,'rep_subj':rep_subj,'rep_subjpass':rep_subjpass,'rep_agent':rep_agent,'nothing':nothing,
                              # Verb labels from NER model, auxiliaries, modals, semi-modals
                              'root':root,'aux':aux,'auxpass':auxpass,'pmod':pmod,'smod':smod,
                              'needaux':needaux,'needroot':needroot,'needneg':needneg,
                              # "Be" as root and delextical verbs
                              'be':be,'have':have,'give':give,'take':take,'make':make,
                              # Other verbs as roots
                              'assist':assist,'draw':draw,'enter':enter,
                              'prepare':prepare,'provide':provide,'propose':propose,'propose2':propose2,'put':put,'forward':forward,
                              'refer':refer,'submit':submit,
                              'adopt':adopt, 'affect':affect, 'apply':apply,'issueroot':issueroot,'remain':remain,'retain':retain,
                              # Negation modifier and prepositions
                              'neg':neg,'by':by,'by2':by2,'by3':by3,'to':to,'to2':to2,
                              # Terms associated with prerogatives and competences
                              'competent':competent,'force':force,'free':free,'prejudice':prejudice,'noeffect':noeffect,'accountable':accountable,'responsible':responsible,
                              'right':right,'right_subj':right_subj,'right_dobj':right_dobj,
                              # Terms associated with instruments
                              'proposal':proposal,'proposal_subj':proposal_subj,'proposal_dobj':proposal_dobj,'legprop':legprop,'recommendation':recommendation,'recommendation_subj':recommendation_subj,
                              'recommendation_dobj':recommendation_dobj,'recommendation_pobj':recommendation_dobj,'opinion':opinion,'opinion_subj':opinion_subj,'opinion_dobj':opinion_dobj, 'opinion_pobj':opinion_pobj,
                              'measure':measure,'measure_subj':measure_subj,'measure_dobj':measure_dobj,
                              'measure_pobj':measure_pobj,'measure_pobj2':measure_pobj2,'teract':teract,
                              # Terms associated with constraints
                              'secrecy':secrecy,'issue':issue,
                              'information':information,'information_subj':information_subj,'information_dobjpobj':information_dobjpobj,
                              'public':public,'good':good,'accordance':accordance,'procedure':procedure,'comitproc':comitproc}


                        # -------------------- CLASSIFICATION --------------------
                        del_ms = classify_del_ms(sent_dict)
                        del_ms2 = classify_del_ms2(sent_dict)
                        so_ms = classify_so_ms(sent_dict)
                        so_ms2 = classify_so_ms2(sent_dict)
                        con_ms = classify_con_ms(sent_dict)
                        con_ms2 = classify_con_ms2(sent_dict)

                        del_nca = classify_del_nca(sent_dict)
                        del_nca2 = classify_del_nca2(sent_dict)
                        so_nca = classify_so_nca(sent_dict)
                        so_nca2 = classify_so_nca2(sent_dict)
                        con_nca = classify_con_nca(sent_dict)
                        con_nca2 = classify_con_nca2(sent_dict)

                        agenda = classify_agenda(sent_dict)
                        del_com = classify_del_com(sent_dict)
                        si_com = classify_si_com(sent_dict)
                        si_com2 = classify_si_com2(sent_dict)
                        con_com = classify_con_com(sent_dict)
                        con_com2 = classify_con_com2(sent_dict)

                        del_age = classify_del_age(sent_dict)
                        si_age = classify_si_age(sent_dict)
                        si_age2 = classify_si_age2(sent_dict)
                        con_age = classify_con_age(sent_dict)
                        con_age2 = classify_con_age2(sent_dict)

                        # -------------------- POSTPROCESSING --------------------
                        if del_ms in ["RIGHT"]:
                            con_ms = None
                        if so_ms in ["G1", "G2", "G1_pass", "G2_pass", "RECOMMEND", "RECOMMEND_pass"]:
                            con_ms = None

                        if del_nca in ["RIGHT"]:
                            con_nca = None
                        if so_nca in ["G1", "G2", "G1_pass", "G2_pass", "RECOMMEND", "RECOMMEND_pass"]:
                            con_nca = None

                        if agenda in ["PROPOSE", "PROPOSE_pass", "SUBMIT", "SUBMIT_pass"]:
                            del_com = None
                        if agenda in ["SUBMIT", "SUBMIT_pass"]:
                            si_com = None
                        if agenda in ["SUBMIT", "SUBMIT_pass"] and con_com in ["AC1", "AC1_pobj"]:
                            con_com = None
                        if si_com in ["G1", "G1_pass", "RECOMMEND", "RECOMMEND_pass"]:
                            del_com = None
                        if con_com in ["C1_opinion", "AC1", "AC1_pobj", "INFORMATION", "INFORMATION_pobj",
                                       "PUBLIC", "PUBLIC_pobj", "REFER"]:
                            del_com = None
                        if con_com in ["INFORMATION", "INFORMATION_pobj", "PUBLIC_pobj"]:
                            si_com = None
                        if con_com in ["COMIT00-22b", "COMIT10-22c"] and del_com in [None] and si_com in [None]:
                            del_com = con_com

                        if si_age in ["G1", "G1_pass", "RECOMMEND", "RECOMMEND_pass"]:
                            del_age = None
                        if con_age in ["C1_opinion", "AC1", "AC1_pobj", "INFORMATION", "INFORMATION_pobj",
                                       "PUBLIC", "PUBLIC_pobj", "REFER", "SECRECY", "SECRECY_pobj"]:
                            del_age = None
                        if con_age in ["INFORMATION", "INFORMATION_pobj", "PUBLIC_pobj"]:
                            si_age = None

                        # -------------------- WRITE ROW --------------------
                        row = (
                            celex, sentence_id, sub_sentence_id, subsub_sentence_id, subsub_sentence_n,
                            length, length_sentence, length_celex,
                            text, root, neg, pmod, smod,
                            del_ms, del_ms2, con_ms, con_ms2, so_ms, so_ms2,
                            del_nca, del_nca2, con_nca, con_nca2, so_nca, so_nca2,
                            agenda, del_com, si_com, si_com2, con_com, con_com2,
                            del_age, si_age, si_age2, con_age, con_age2,
                            subj, subjpass, subj2, subjpass2, dobj, dobj2, agent, agent2,
                            pobj, pobj2, pobj3, pobj4, pobj5, pobj6, pobj7,
                            compound, compound_subj,
                        )
                        csv_writer.writerow(row)

            if (k + 1) % 10000 == 0:
                print(f"Processed {k+1:,} sentences...")

stop = timeit.default_timer()
execution_time = stop - start
print(f"\n✅ Program executed in {execution_time:.2f} seconds.")
print(f"→ Output files saved to:\n  - {output_file}\n  - {destination_file}")
