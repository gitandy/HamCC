HamCC - CassiopeiaConsole
=========================

CassiopeiaConsole or short HamCC allows to quickly type in Ham Radio QSOs via commandline sessions.
During online QSOs, transfer handwritten logs or maybe when going through a bunch of QSO paper cards.

The special mini language used is somewhat inspired by [hostilog](https://df1lx.darc.de/hosti-logger/) by Peter, DF1LX.

CassiopeiaConsole is designed to be used as an API in other programs to support a textbased interface 
but can also be used as standalone console logger.

The name
--------
Searching for a name was not very easy. But on my daily walk with our cat I tend to watch the stars while she 
is wandering through the gardens nearby guarding her territory (and she can be very patient with that).

So Cassiopeia came to my mind, as the constellation is very prominent in front of the Milkyway.

Cassiopeia, it is said, upset the gods when she claimed to be more beauty than the Nereids.
What a lucky circumstance as CassiopeiaConsole claims to be the fastest logger around...

HamCC as a program
--------------------
You may set your call, your name and your locator via arguments.

    # hamcc -c DF1ASC -n Andreas -l JO30ui

After starting the program you will see different rows.

    | */- | d 2024-08-20 | t 18:58 | B 15m | M SSB | C  | @  |
    QSO> _ 
    Diagnose information

- The first row shows the information already available for the current QSO. 
  The signs left most in each box are corresponding to the format characters.
  - The star in the first box shows, that you are editing a new QSO. 
    It may show the number of a cached QSO you are about to edit
  - The dash in the first box shows, that there are no further unsaved QSOs. 
    Otherwise, it shows the count of cached QSOs
- The second row shows the command prompt where you will type in the QSO
- The third row may show status or format error information

Just start typing at the command prompt.

Think of the whole QSO as a sentence and the information like band, callsign, etc. are the words.

If you hit the SPACE-key the current information (word) will be evaluated.
If you hit ENTER the QSO (sentence) will be saved and the input will be cleared for a new QSO.

There is a step back as long the QSO is not written to disk.

These commands will only work when run as program
* Typing ! will write all QSOs (if any, see first box in first row) to disk
* Key UP/DOWN scrolls through available QSOs
* DEL key deletes the selected QSO
* CTRL-C writes all QSOs to disks and quits the program

HamCC stores the QSOs in ADIF 3.x ADI format (via [PyADIF-File](https://github.com/gitandy/PyADIF-File#pyadif-file)).
Per default the file HamCC_log.adi in your user home will be used. If you are using the same file every time, 
new logs will be appended. 
This behaviour and the file path can be changed via arguments (run HamCC -h for further information).

Some graphical loggers (i.e. [DragonLog](https://github.com/gitandy/DragonLog?tab=readme-ov-file#dragonlog)) are 
able to watch for ADI file changes from other programs and immediately import new QSOs.

CassiopeiaConsole minilanguage
------------------------------
The single words must conform to a format to be evaluated as valid QSO information.

Example session

1. Type in 8 or 80m followed by SPACE and HamCC recons you are using the 80m band 
2. Now type s or ssb and HamCC saves the mode SSB after you hit SPACE
3. We are ready for the first QSO? Ah, DF1ASC is calling so type it in and hit SPACE (I won't repeat it from now on)
4. He told you his name Andreas and we prefix it like 'Andreas
5. You want to leave some comments? Type in "#Ant Dipol, Rig FT-991A"

Your console should look something like

    | */- | d 2024-08-20 | t 19:37 | B 80m | M SSB | C DF1ASC | @  | ' Andreas | # Ant Dipol, Rig FT-991A |
    QSO> 8 s df1asc 'Andreas "#Ant Dipol, Rig FT-991A" _

After hitting ENTER the QSO will be cached (number of cached QSOs is displayed, see marking) and some 
information will be stored for the next QSO.

        v
    | */1 | d 2024-08-20 | t 19:37 | B 80m | M SSB | C  | @  |
    QSO> _

The table shows all available pre- and postfixes. The following will work for API and if run as program.

Placeholder x for characters and 9 for numbers.
Types marked with auto are prefilled but can be overwritten. Types marked with memory are retained for the session.

| Info         | Format          | Type    | Comments                    |
|--------------|-----------------|---------|-----------------------------|
| Callsign     | xx9xx           |         | format checked              |
| Locator      | @xx99xx         |         | format checked              |
| Name         | 'xxxx           |         | _ for spaces                |
| Comment      | #xxxx           |         | _ for spaces                |
| Band         | valid ADIF band | memory  |                             |
| Mode         | valid ADIF mode | memory  |                             | 
| RST rcvd     | .599            | auto    | default CW 599, phone 59    |
| RST sent     | ,599            | auto    | default CW 599, phone 59    |
| QSL rcvd     | *               |         | toggles the information     |
| Contest ID   | $xxxxxx         | memory  |                             |
| Rcvd QSO ID  | %xxxxx          |         |                             |
| Time         | HHMMt           | memory  | partly time will be filled  |
| Date         | YYYYMMDDd       | memory  | partly date will be filled  |
| Date/Time    | =               | auto    | sync date/time to now       |
| Frequency    | 99999f          |         | in kHz                      |
| TX Power     | 99p             |         | in W                        | 
| Your Call    | -cxx9xx         | memory  |                             | 
| Your Locator | -lxx99xx        | memory  |                             | 
| Your Name    | -nxxxx          | memory  | _ for spaces                |
| Finish QSO   | linefeed        | command | ENTER-Key                   |
| Clear QSO    | ~               | command | clears input not cached QSO |
| Show QSO     | ?               | command |                             |

For callsigns, mode, locators, RST and contest id lowercase will be converted to uppecase.

Some info allows to use _ which will be converted to spaces. 

    QSO> #Long_comment 'Long_name

It is also possible to enclose the sequence in quotes to type spaces instead.

    QSO> "#Long comment" "'Long name"

RST fields supports the whole range like 59 for phone, 599 for CW or -06 for digimodes. 
For CW the last digit can also be an a for aurora, s for scatter or alike 
(see [R-S-T System](https://en.wikipedia.org/wiki/R-S-T_system) on Wikipedia).

If you only give minutes to time i.e. 23t the time will be filled with the last hour as if 1823t was given 
(assuming last time is something like 18:12 or so).
For partial dates it will be filled in the same manner for each 2 digits missing from left to right. 
So the date 240327d, 0327d or 27d will be filled as if 20240327d was given.

### hostilog shortcuts for bands and modes
HamCC also supports the [hostilog shortcuts](https://github.com/gitandy/HamCC/blob/master/HOSTILOG_SHORTCUTS.md]) 
for modes and bands (bands limited to hostilog shortwave mode).
Only the mode shortcut d will result in MFSK for ADIF compatibility.

HamCC adds two shortcuts for modes
* m for MFSK (which also works via d)
* dv for DIGITALVOICE

### Contests
If you typed in a contest id HamCC starts to increase a QSO contest reference (see marked in example)
which you may want to communicate to your QSO partners.
Changing the contest id resets the QSO counter.

                                                                       v
    | d 2024-08-20 | t 13:06 | B 10m | M SSB | C  | @  | $ ARRL-10 | N 1 | % 007 |
    QSO> $ARRL-10 %007 _

The received contest data will simply be stored without further handling (currently).

To leave the contest mode for the following QSOs type a single $ followed by a SPACE.

Source Code
-----------
The source code is available at [GitHub](https://github.com/gitandy/HamCC)

Copyright
---------
HamCC - CassiopeiaConsole &copy; 2024 by Andreas Schawo is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
