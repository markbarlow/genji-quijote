
General:
Choice of the J for Quijote
The source texts

Check CLAUDE.md and README.md for what it says already, and current about:
 ~1,021 literary mashup sentences combining The Tale of Genji (first half) and Don Quixote (second half), in the exquisite-corpse tradition.
A literary mashup web app combining *The Tale of Genji* and *Don Quixote* in the exquisite-corpse tradition. Each pair joins the first half of a sentence from Genji with the second half of a sentence from Quixote — exploiting the tonal contrast between Genji's interior, melancholy register and Quixote's comic, earthy one.

 Pipeline reads the source texts, cleans and segments them into sentences, halves each sentence at a clause boundary, scores sentence halves, and pairs the top-scoring Genji halves with top-scoring Quixote halves.

 Both texts are in the public domain via Project Gutenberg:

 - *The Tale of Genji* — Murasaki Shikibu, tr. Suematsu Kenchio
 - *Don Quixote* — Miguel de Cervantes, tr. John Ormsby

1,021 pairs, generated offline from the Project Gutenberg texts and served as a static site on GitHub Pages.


A creative mashup project combining The Tale of Genji and Don Quijote — both public domain, available on Project Gutenberg. Working title: "The Shining Prince meets The Knight Errant".

combining the first half of a sentence from one work with the second half from the other — like the surrealist "exquisite corpse" technique. The tonal contrast is rich: Genji is interior, seasonal, melancholy, full of mono no aware; Quijote is comic, delusional, earthy, Sancho always deflating the heroics.

I often use the Spanish "Quijote" here as a synonym for "Quixote" which is the usual English translation. In the text you will find Quixote as it is English.

Process involved iterating through random sample generations to build up a set of heuristics. For example, excluding problematic text such as XYC (removing footnotes, latin text in Quijote, boilerplate, Weak terminals are articles, bare prepositions, coordinating conjunctions,and any 1–2-character alphabetic token e.g. the a an by on or. ) and favouring snippets featuring characters with classification of major and minor. Minimum half lengths.

Assigns a raw floating-point score to a cleaned sentence based on four
weighted components: length (sweet-spot), character presence, place-name
heuristic, and lexical diversity (type-token ratio).

Character ranking for major and minors


Generated 2,000 for final review.
Cut just under 612
Edited 361 - limited myself to editing the end of a Genji or the start of a Quijote, nothing more, to remain faithful to the source.
The remainder
This bit was rather painstaking.
The 10,21



  Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum — some
  explanation of the background. Each mashup joins the first half of a
  sentence from Murasaki Shikibu's <em>Tale of Genji</em> with the second
  half of a sentence from Cervantes' <em>Don Quijote</em>.

  Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum Lorem ipsum — some
  explanation of the background. Both texts in the public domain via
  Project Gutenberg.
</p>


- blog post todo
- related todo 

-----------

gq-0463
For example, her stepmother had even held her responsible for Makibashira's fall; and Don Quixote went some twelve paces forward to meet her.


gq-0486
Having delivered this message Koremitsu brought in some of Genji's servants and went home to his village to wait there for Don Quixote, who was coming after him.

gq-0488
Although it was early days to begin thinking about the little Akashi Princess's Initiation, the duchess was as much delighted as Don Quixote was driven to desperation.

gq-0016
After performing before the Emperor, the Mummers visited the quarters of Lady Akikonomu, to describe the end of the government of the great Sancho Panza, flower and mirror of all governors of islands.

gq-0006
Koremitsu had patiently continued the enquiry and got his master's blessing, which Don Quixote gave him with tears, and he received blubbering.

gq-0013
The Emperor had heard that Genji was still on intimate terms with his aunt the Princess Oborozuki, and that Don Quixote and Sancho should be conducted to their old quarters.

gq-0019
Hyōbukyō could not fail to notice that Genji was suddenly related to Don Quixote.

gq-0014
But under the influence of Kōkiden, who had subsequently thrust Oborozuki upon him, in imitation of the lovers of Marcela.

gq-0096 - their classic preoccupations
She was no great beauty, Genji reflected, and Sancho asked the landlord what he had to give them for supper.

gq-0113
What a queer place to be lying in! thought Genji, fancying himself the most valorous knight-errant of the age in the world because of his late victory.

gq-0143 unexpected influence
The princess’s ancient gentlewomen realized that Genji did not approve of their mistress’s taste in colours till Sancho, perceiving that daybreak was coming on apace, very cautiously untied Rocinante and tied up his breeches.

gq-0175
This news was brought to Genji in the Palace and the curate contrived with no small trouble to get Don Quixote on the bed, and he fell asleep with every appearance of excessive weariness.

gq-0188 oh faithful Sancho
The high position to which Genji had been raised two years ago had entailed much tiresome business for six days, during which he was often visited by his friends the curate, the bachelor, and the barber, while his good squire Sancho Panza never quitted his bedside.

gq-
Genji continued to visit him as before and was assiduous in his attention to Aoi’s maids-of-honour, and they soon had him well soaped and washed, and having wiped him dry they made their obeisance and retired.

gq-0201 a painful banging into a drawer
Genji detained the messenger, and going to his desk opened the drawer where he kept his Chinese writing-paper and had his ribs a little bruised.

gq-0244 Rocinante priest reading the signs
The old priest looked in his calendar, chose a lucky day, and peered between the legs of Rocinante to see if he could now discover what it was that caused him such fear and apprehension.

gq-0268 off to Seville
It was well known in society that Genji must not go to Seville until he had cleared all these mountains of highwaymen and robbers, of whom report said they were full.

gq-0279 naughty Sancho!
Tō no Chūjō took the _wagon_, which he played, and soundly kicked by Sancho, was on all fours feeling about for one of the table-knives to take a bloody revenge with.

gq-0327 lifting spirits at the palace
The move to Genji’s Palace and shrewd sayings of Don Quixote and the humours of his squire Sancho Panza could not help giving general pleasure to all the world.

gq-0383 he's Genji's squire now?
While he was about it Genji thought that he had better tell Yūgiri too, he warned his squire Sancho of the day and hour he meant to set out, that he might provide himself with what he thought most needful.

gq-0412 casting aspersions on Genji and Dulcinea
Genji had of course for some while past known my lady Dulcinea; for there must have been kings in the world who kept mistresses.

gq-0468 Emperor and the Asturian inn servant
Every one at Court came to enquire after his progress; the Emperor grappled with Maritornes, and he and she between them began the bitterest and drollest scrimmage in the world.

gq-0529 Genji - off to the Indies in a huff
Meanwhile Genji, in a frenzy of irritation and disappointment, decided upon going to the Indies, embarking the portion that fell to him in trade.

gq-0601 Genji - an indiscriminate painter
Jijū and the other ladies-in-waiting had heard so much about Genji who came here to paint anything that might turn up.

gq-0618 Murasaki not keen on Ricote, ageist?
Murasaki had already heard they were all good-looking young fellows, except Ricote, who was a man somewhat advanced in years.

gq-0682 Genji narcoleptic and mad
She went on to pour out such a pitiful tale of things gone awry that Genji could bear it no longer, and once more he fell asleep, leaving them marvelling at his madness.

gq-0823 Emperor inappropriate musical compulsions
The Emperor could hardly contain lewd or loose songs either by day or night.


gq-0987 Genji not so gorgeous after all
At the summons of the herald Genji and Tō no Chūjō now appeared and with them Genji’s half-brother, see what hideous countenances come to frighten us!

gq-1007 Genji and Quijote love rivals?
Genji was rather disappointed that she at once set about tending Don Quixote, and made her young daughter, a very comely girl, help her in taking care of her guest.

gq-1013 Genji darker martial side hitherto undocumented
Genji did not rise till the Turks acknowledged he did it merely for the sake of doing it, and because he was by nature murderously disposed towards the whole human race.

gq-1019 Genji mockery gets under DJ's skin
Genji was afraid that his and their laughter acted like gunpowder on Don Quixote’s fury, for drawing his sword without another word he made a rush at the stand.

gq-

gq-

gq-

gq-
gq-


gq-

gq-

gq-

gq-

gq-

gq-

gq-

gq-
gq-


gq-

gq-

gq-

gq-

gq-
