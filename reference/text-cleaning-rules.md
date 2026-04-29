# RAC Story Text — Cleaning Rules

**Purpose:** Rules for cleaning the body text (the "text" field from the submission) before it's published as `ContentDescription` on the Intranet. Used by the `intranet-post` skill at the cleaning step.

**Core principle:** Cleanup, not rewriting. The skill's job is to remove the artefacts of dictation and informal writing — not to "improve" the submitter's prose, reorder their thoughts, or polish their voice into something more "professional." If cleaned text reads more like the submitter and less like a marketing department, the skill is working.

**The most sophisticated thing the skill can do is sometimes nothing.** A submission that's already well-written gets passed through untouched. Recognising that takes more skill than reflexively cleaning.

---

## What to remove

### 1. Filler words

Words that add no meaning and signal hesitation or thinking-out-loud. Almost always artefacts of dictation.

**Always remove (when used as filler):**
- *um*, *uh*, *er*, *ah*
- *you know* (when used as a hedge, e.g. "we went down to, you know, the quarry")
- *like* (when used as filler, e.g. "we like, totally fixed the trailer")
- *sort of*, *kind of* (when used as a hedge, e.g. "we sort of figured out the issue")
- *I mean* (when used as a self-correction marker)
- *basically*, *literally* (when used as filler — almost always)

**Examples:**

> Before: *"Yeah look, um, we went down to the quarry, you know, and uh, fixed the trailer basically."*
> After: *"We went down to the quarry and fixed the trailer."*

> Before: *"It was, like, a really good day, sort of, with the team."*
> After: *"It was a really good day with the team."*

**Important — when these words are NOT fillers, leave them alone:**

- *"I like the new kitchen"* — *like* is a verb here, not filler. Keep it.
- *"That's the kind of work we do"* — *kind of* is meaningful here. Keep it.
- *"You know what I mean?"* — *you know* in a direct address. Could be conversational warmth. Keep it.

The test: does removing the word change the meaning or the warmth? If yes, leave it. If no, remove it.

### 2. Stutters and self-corrections

When dictation captures someone restarting a thought.

**Examples:**

> Before: *"The kids the kids did a workshop today."*
> After: *"The kids did a workshop today."*

> Before: *"We went to we drove down to the quarry."*
> After: *"We drove down to the quarry."*

> Before: *"I think I mean we should ask Sam."*
> After: *"We should ask Sam."*

**The rule:** when the same phrase appears twice immediately in succession, keep the second instance. When someone starts a sentence and restarts it differently, keep the restart.

**Edge case:** intentional repetition for emphasis stays.

> Keep: *"It was a long, long day."* — emphasis, not stutter.
> Keep: *"We did it. We actually did it."* — rhetorical emphasis.

The test: was the repetition deliberate or accidental? If you'd read it aloud as deliberate emphasis, keep it. If it sounds like a false start, remove the false start.

### 3. Swear words

Remove cleanly. Repair grammar around the removal. **Do not asterisk.** Do not flag the submission. Just clean.

**Examples:**

> Before: *"This bloody trailer wouldn't start."*
> After: *"This trailer wouldn't start."*

> Before: *"What a shit day at the office."*
> After: *"What a day at the office."*

> Before: *"We worked our arses off to get it done."*
> After: *"We worked hard to get it done."*

**Note on the third example:** simple removal would leave *"We worked our off to get it done"* which is broken grammar. The skill needs to repair the sentence — replacing *"our arses off"* with *"hard"* preserves the intent (effort, intensity) without the swear.

**Common swear/hedge replacements that preserve meaning:**
- *"bloody [thing]"* → just *"[thing]"* (the intensifier is removed)
- *"worked our arses off"* → *"worked hard"* / *"worked flat out"*
- *"shit day"* → *"hard day"* / *"long day"* / *"rough day"* (pick based on context)
- *"piss-easy"* → *"easy"* / *"straightforward"*
- *"bugger all"* → *"very little"* / *"hardly any"*

**Mild Australianisms that aren't really swears in this context:**
- *"crook"* (sick or broken) — keep, this is regular Aussie English
- *"stuffed"* (broken or tired) — keep, contextual
- *"bugger"* as a standalone exclamation in dialogue — borderline; remove if it's the speaker's own narration, keep if it's reported speech with quotation marks

The test: would this word make a senior manager wince to read on the published Intranet? If yes, remove. If it's just regional vernacular, keep.

### 4. Sentence-level mechanics

Always done, low-risk, makes a huge difference:

- **Capitalise sentence starts.** Dictation often produces all-lowercase output.
- **Add terminal punctuation if missing.** Periods at the end of sentences, even if the speaker didn't pause to indicate one.
- **Fix spoken punctuation markers.** *"comma"* / *"full stop"* / *"new paragraph"* spoken aloud become actual punctuation.
- **Paragraph breaks at obvious topic shifts.** A 200-word run-on of dictation usually has 2-3 natural break points. Insert blank lines between them.

**Example:**

> Before: *"yeah we went down to the quarry trailer was broken comma so we got stuck in full stop took about two hours all up but we got it sorted"*
>
> After: *"We went down to the quarry. Trailer was broken, so we got stuck in. Took about two hours all up, but we got it sorted."*

---

## What NEVER to do

These rules are absolute. Violating any of them is a worse outcome than leaving the original text untouched.

### Never paraphrase

> Before: *"We worked hard to get the trailer back on the road."*
> Wrong (paraphrase): *"The team demonstrated exceptional dedication in returning the trailer to operational status."*
> Wrong (paraphrase): *"Through diligent effort, our team successfully restored the trailer."*
> Right: *"We worked hard to get the trailer back on the road."* — leave it alone.

If the submitter's words are already clean, the skill's job is done. Paraphrasing for any reason — to "elevate" the language, to make it more formal, to fit a tone — is voice erasure.

### Never reorder sentences

The submitter chose to put information in a particular order. That order is part of the story. Don't decide that information would be "better" earlier or later.

### Never add information that wasn't in the submission

> Before: *"We went down to the quarry."*
> Wrong: *"This morning, members of our team went down to the quarry to assess maintenance needs."*

You don't know it was this morning. You don't know if it was members of the team or one person. You don't know it was for assessment. Stick to what was actually said.

### Never "fix" informal grammar that's part of voice

- *"Us mob went down to the kitchen"* — keep. This is Aboriginal English and it's correct, intentional, and part of RAC voice.
- *"Me and Sam went to the quarry"* — keep. This is informal but standard spoken English. Don't "correct" to "Sam and I" — that's a register shift, not a cleanup.
- *"Yeah nah but it was good"* — keep the "yeah nah" if it's how someone speaks. Australian English.
- *"He done good today"* — borderline. If it's clearly the submitter's natural speech, keep. If it looks like a transcription error, gently fix to "He did good today."

The test: does this sound like the submitter's natural voice, or does it sound like a typo? Voice stays. Typos get fixed.

### Never correct or translate non-English words

This rule is non-negotiable.

> If the submission contains: *"Gululu yuta yothu ngayiwuy Nhulunbuy"*
> The cleaned text contains: *"Gululu yuta yothu ngayiwuy Nhulunbuy"*

No spelling "corrections." No added translations. No italicisation. No footnotes. The Yolŋu words are part of RAC voice and they appear as the submitter wrote them.

If a word looks unfamiliar and the skill is uncertain, **the safe default is always to leave it alone.** It's almost certainly a name, place, term, or phrase the submitter chose deliberately.

This applies to Yolŋu most prominently but covers any non-English content — Greek family names, Vietnamese place names, French terms, anything.

### Never alter proper names

> If the submission says *"Maggie Garawirrtja"* — that's exactly what the cleaned text says.
> If the submission says *"Bunumbirr"* — that's exactly what the cleaned text says.
> If the submission says *"Rachael.S"* — that's exactly what the cleaned text says, dot and all.

Submitters know how to spell their colleagues' and members' names. The skill does not. If a name looks unusual, that's because it's an actual person's actual name, not a typo.

If unsure whether a string is a name, leave it alone. The cost of treating a name as a typo (offending someone) is much higher than the cost of treating a typo as a name (one strange spelling on the Intranet).

### Never apologise or hedge in cleaned output

If the submitter said *"this is probably nothing but..."* — the cleaned version still says *"this is probably nothing but..."*. Don't strengthen it. Don't soften it. Don't editorialise.

---

## When the submitter has already written it well

This is the hardest discipline and the most important.

**Signs the submission is already clean:**
- No filler words
- Complete sentences with proper punctuation
- Clear flow
- Natural voice (not stiff, not chaotic)
- Probably typed deliberately rather than dictated

**What the skill should do:** nothing. Pass it through untouched.

**Example — Sam at the quarry, typed version:**

> Submission: *"All in a day's work for the Bus.Dev manager helping out the guys to get the trailer back on the road. Job done!"*
>
> Cleaned: *"All in a day's work for the Bus.Dev manager helping out the guys to get the trailer back on the road. Job done!"*
>
> AdminNote: *"Submitter's text used verbatim."*

The temptation to "improve" already-good text is the skill's worst failure mode. *"All in a day's work"* is excellent voice. *"In keeping with our manager's hands-on leadership ethos"* is voice failure. The skill must resist the urge to add value where no value-add is needed.

**Test:** if a submission would be embarrassing to publish as-is, the skill cleans it. If it would be fine to publish as-is, the skill leaves it alone (and notes that in AdminNote).

---

## Logging what was cleaned

The skill keeps track of what it cleaned and reports it in the AdminNote field on the sheet row. This gives the reviewer transparency about what the skill did.

**Format:** `"Auto-cleaned: [count] fillers, [count] swears removed. [other actions]"`

**Examples:**

- *"Auto-cleaned: 3 fillers, 1 swear removed. Title generated."*
- *"Auto-cleaned: 2 fillers removed. Submitter's title and highlight used verbatim."*
- *"Submitter's text used verbatim. Title and highlight generated."*
- *"Submitter's text, title and highlight used verbatim."*

Keep it short. The reviewer sees this in the sheet, not a separate report — it has to fit in a column.

---

## Handling thin signal

Sometimes a submission has very little text — maybe twenty words, maybe just a caption. The cleaning rules still apply, but with extra restraint.

**Example:**

> Submission text: *"team day at the kitchen everyone had a good time"*
>
> Cleaned: *"Team day at the kitchen. Everyone had a good time."*

That's it. Don't expand to *"Our team enjoyed a wonderful day together at the Yanawal Kitchen, with everyone reporting a positive experience."* That's fabrication.

If there's not much to clean, there's not much to clean. Brevity is fine.

---

## What the skill does NOT clean

**The Title field** (if the submitter wrote one). Use as-is, typos and all. Submitter's title stays.

**The Highlight field** (if the submitter wrote one). Same — use as-is.

**Photo filenames or alt-text.** Out of scope.

The cleaning rules apply *only* to the `text` field that becomes `ContentDescription`. Title and highlight cleaning would risk the skill imposing its taste on submitter's deliberate choices.

---

## Notes for the skill

When processing a submission:

1. **First, read the text carefully.** Decide: does this need cleaning, or is it already clean?
2. **If already clean:** pass through, log "verbatim" in AdminNote, move to title/highlight generation if needed.
3. **If needs cleaning:** apply rules in order — fillers first, stutters second, swears third, mechanics last (capitalisation, punctuation, paragraph breaks).
4. **Re-read the cleaned text.** Does it still sound like the submitter? If it sounds more polished or more "professional", you've over-corrected. Roll back.
5. **Preserve all proper names and non-English words exactly.** When uncertain, leave alone.
6. **Count what was changed** for the AdminNote.
7. **Never paraphrase. Never reorder. Never add. Never translate.**

The goal: a reader of the cleaned text should think "that sounds like Sam wrote it" — not "that sounds like a press release about Sam."
