#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import re
import math

dir = os.path.dirname(sys.argv[0])
f = open(dir + "/abrechnung.txt")

context = None

def exchook(exctype, value, tb):
	print
	print "----------------------------------------------"
	print "Exception:", value
	global context
	print "Current context:", context
	print "Traceback:"
	import traceback
	traceback.print_tb(tb)

sys.excepthook = exchook
Err = Exception

def geld(v):
	return str(round(v,2)) + " €"

getraenkTypen = set([ "A", "Wasser", "Cola", "O", "Bier" ])

class Stand:
	def __init__(self):
		self.rechnungNochOffen = None
		self.geldInKasse = 0.0
		self.getraenkePreise = {}
		self.getraenke = {}
		
		for g in getraenkTypen: self.getraenke[g] = 0

	def handleBestellung(self, bestellung):
		if bestellung.bezahlt:
			self.geldInKasse -= bestellung.bezahlt + bestellung.trinkgeld
			desc = "-" + geld(bestellung.bezahlt)
		else:
			self.rechnungNochOffen = best
			desc = "offen"

		for g in getraenkTypen:
			if g in bestellung.preise:
				self.getraenkePreise[g] = bestellung.preise[g]

		self.dump("Bestellung (" + desc + ")")
		
	def handleAbrechnung(self, abr, letzteBest):
		if self.rechnungNochOffen: raise Err, "kann Abrechnung nicht machen, wenn noch eine Rechnung offen steht; offen stehende Rechnung vom " + self.rechnungNochOffen.date
		self.geldInKasse += abr.summe
		self.dump("Abrechnung (+" + geld(abr.summe) + ")")
		g = self.geldInKasse + letzteBest.pfandRueckgabe - letzteBest.trinkgeld
		print "  mit Pfandrückgabe (+" + geld(letzteBest.pfandRueckgabe) + ") und Trinkgeld(-" + geld(letzteBest.trinkgeld) + ") :", geld(g), "(~= -Wert der noch vorhandenen Flaschen)"
		
	def dump(self, desc):
		print "Geld in Kasse nach", desc, ":", geld(self.geldInKasse), " noch eine Rechnung offen" if self.rechnungNochOffen else ""
		
stand = Stand()

def wertVonGetraenken(getraenke):
	global stand, getraenkTypen
	geld = 0.0
	for g in getraenkTypen:
		if g in getraenke:
			#print g, "da:", self.getraenke[g], "  preis:", self.getraenkePreise[g]
			geld += getraenke[g] * stand.getraenkePreise[g] 
	return geld



class Bestellung:
	def __init__(self, date):
		global getraenkTypen
		self.date = date
		self.getraenke = {}
		for g in getraenkTypen: self.getraenke[g] = 0
		self.preise = {}
		self.betrag = 0
		self.pfand = 0
		self.bezahlt = None
		self.trinkgeld = None
		self.pfandRueckgabe = None

	def __str__(self):
		return "Bestellung vom " + self.date

	def finalize(self):
		for getraenkTyp in self.getraenke:
			stand.getraenke[getraenkTyp] += self.getraenke[getraenkTyp]

		print \
			"Bestellung", self.date, ":", \
			self.betrag, "€", \
			" Pfand:", self.pfand, "€", \
			" Summe:", self.betrag + self.pfand, "€"
		if self.bezahlt:
			if self.trinkgeld is None: raise Err, "Trinkgeld wurde in Bestellung vom " + self.date + " nicht angegeben"
			self.pfandRueckgabe = self.betrag + self.pfand - self.bezahlt
			print "  bezahlt:", geld(self.bezahlt), " Differenz (Pfandrückgabe):", geld(self.pfandRueckgabe), " Trinkgeld:", geld(self.trinkgeld)
		else:
			print "  noch nicht bezahlt"

	@staticmethod
	def getraenkTyp(name):
		if "Apfelschorle" in name: return "A"
		if "Kastell" in name: return "Wasser"
		if "Wasser" in name: return "Wasser"
		if "Cola" in name: return "Cola"
		if "Orange" in name: return "O"
		if "Bitburger" in name: return "Bier"
		raise Err, "Getränk " + name + " unbekannt!"

	def handle(self, l):
		getraenkeTrinkgeldRE = re.compile("^Trinkgeld: (?P<Betrag>[0-9,.]+) *$", re.UNICODE)
		m = getraenkeTrinkgeldRE.match(l)
		if m:
			self.trinkgeld = float(m.group("Betrag").replace(",","."))
			return

		getraenkeBezahltRE = re.compile("^bezahlt: (?P<Betrag>[0-9,.]+) *$", re.UNICODE)
		m = getraenkeBezahltRE.match(l)
		if m:
			self.bezahlt = float(m.group("Betrag").replace(",","."))
			return

		getraenkRE = re.compile("^" +
			"(?P<Getraenk>[\w ]+) (?P<FlaschenAnzahl>\d+)x(?P<FlaschenInhalt>[0-9,.]+): *" +
			"(?P<KaestenAnzahl>[0-9,.]+) *\* *(?P<KastenPreis>[0-9,.]+)" +
			" *$", re.UNICODE)

		einkaufEinzelnRE = re.compile("^einzeln: +" +
			"(?P<Getraenk>[\w ]+): +" +
			"(?P<FlaschenAnzahl>[0-9,.]+) *\* *(?P<FlaschenPreis>[0-9,.]+)" +
			" *$", re.UNICODE)

		leergutRE = re.compile("^Leergut: +" +
			"(?P<Getraenk>[\w ]+): +" +
			"(?P<KaestenAnzahl>[0-9,.]+) *\* *" +
			"(?P<FlaschenAnzahl>\d+)x(?P<FlaschenInhalt>[0-9,.]+) +Kasten" +
			" *$", re.UNICODE)

		m1 = einkaufEinzelnRE.match(l)
		m2 = leergutRE.match(l)
		m3 = getraenkRE.match(l)
		m = m1 or m2 or m3
		if not m:
			raise Err, "Error, I don't understand (context Bestellung): " + l
		
		Getraenk = m.group("Getraenk")
		
		GetraenkTyp = self.getraenkTyp(Getraenk)
		# WARNING: Wenn das jemals geändert wird, muss sehr aufgepasst werden,
		# dass bisherige Abrechnungen sich nicht ändern. Also am besten
		# einen Datumscheck.
		KastenPfand = 1.5
		FlaschenPfand = 0.15
		if Getraenk == "Kastell Apfelschorle": FlaschenPfand = 0.25 # sind PET flaschen
		if GetraenkTyp == "Bier": FlaschenPfand = 0.08

		if m1: # einzeln
			FlaschenAnzahl = int(m.group("FlaschenAnzahl"))
			FlaschenPreis = float(m.group("FlaschenPreis").replace(",","."))
			betrag = FlaschenAnzahl * FlaschenPreis
			pfand = FlaschenAnzahl * FlaschenPfand
			
			self.betrag += betrag
			self.pfand += pfand
			self.getraenke[GetraenkTyp] += FlaschenAnzahl

		elif m2: # Leergut
			KastenAnzahl = int(m.group("KaestenAnzahl"))
			FlaschenAnzahl = int(m.group("FlaschenAnzahl")) # obwohl nicht gebraucht im Mom. aber macht vielleicht was für den Kastenpfand aus
			pfandkasten = KastenAnzahl * KastenPfand
			
			self.pfand += pfandkasten

		elif m3: # normal
			KastenAnzahl = int(m.group("KaestenAnzahl"))
			KastenPreis = float(m.group("KastenPreis").replace(",","."))
			FlaschenAnzahl = int(m.group("FlaschenAnzahl"))
			
			betrag = KastenAnzahl * KastenPreis
			pfandkasten = KastenAnzahl * KastenPfand
			pfandflaschen = KastenAnzahl * FlaschenAnzahl * FlaschenPfand
			self.betrag += betrag
			self.pfand += pfandkasten + pfandflaschen

			self.getraenke[GetraenkTyp] += FlaschenAnzahl * KastenAnzahl

			FlaschenPreis = KastenPreis / FlaschenAnzahl

		if not m2: # not Leergut
			if GetraenkTyp in self.preise and self.preise[GetraenkTyp] != FlaschenPreis:
				raise Err, "Getränktyp " + GetraenkTyp + " doppelt und Preis unterschiedlich"
			self.preise[GetraenkTyp] = FlaschenPreis
			


class Abrechnung:
	def __init__(self, date):
		self.date = date
		self.personen = {}
		self.summe = None
		self.nochda = None
		self.fehltGeldFlaschen = None
		self.betragForChecking = None

	def __str__(self):
		return "Abrechnung vom " + self.date

	def preFinalize(self):
		if self.nochda is None: raise Err, "'noch da' wurde nicht in Abrechnung vom " + self.date + " angegeben"

		# Verluste durch fehlende Flaschen ausrechnen
		#print "theoretisch noch da:", stand.getraenke, "; noch da:", self.nochda
		fehlt = {}
		fehltGeldFlaschen = 0
		global getraenkTypen
		for g in getraenkTypen:
			if not g in self.nochda: self.nochda[g] = 0
			f = stand.getraenke[g] - self.nochda[g]
			if f != 0: fehlt[g] = f
			# nur den wirklich fehlenden Betrag berechnen -- ignoriere, wenn mehr berechnet wurde als eigentlich da war
			if f > 0: fehltGeldFlaschen += f * stand.getraenkePreise[g] 
			stand.getraenke[g] = self.nochda[g]
		if len(fehlt) > 0: print "nach Abrechnung vom", self.date, "fehlt:", fehlt, geld(fehltGeldFlaschen)
		self.fehltGeldFlaschen = fehltGeldFlaschen

		for g in getraenkTypen:
			if self.nochda[g] == 0:
				del self.nochda[g]

		print "noch vorhandene Flaschen:", self.nochda, geld(wertVonGetraenken(stand.getraenke))
		
	def finalize(self, letzteBest):
		print "Abrechnung vom", self.date, ":"
		
		# zu bezahlende Beträge anhand Anzahl Flaschen
		personen = {}
		for (p,getraenke) in self.personen.items():
			psum = 0
			for (g,count) in getraenke.items():
				psum += stand.getraenkePreise[g] * count
			personen[p] = psum

		bezahlenInsg = sum(personen.itervalues())
		print "  zu bezahlen:", geld(bezahlenInsg), "(insgesamt ohne Verluste gerechnet)"
		print "  Stand:", geld(stand.geldInKasse + wertVonGetraenken(self.nochda)), "(Kasse + Wert von noch vorhandenen Getränken)"
		if not letzteBest.pfandRueckgabe: raise Err, "letzte Bestellung vom " + letzteBest.date + " wurde noch nicht bezahlt, daher noch unbekannt, wie viel Pfand wir zurückbekommen, daher kann fehlendes Geld nicht berechnet werden"
		fehltGeld = - (stand.geldInKasse + wertVonGetraenken(self.nochda) + letzteBest.pfandRueckgabe - letzteBest.trinkgeld + bezahlenInsg)
		print "  fehlendes Geld:", geld(fehltGeld), "(-Stand - zu bezahlen - letzte Pfandrückgabe + Trinkgeld)"
		# in seltenen Fällen, wenn Pfand wiedergefunden wurde o.Ä., haben wir fehltGeld<0, also kriegen wir etwas wieder
		# bei unserer allerersten Abrechnung ist es sogar noch mehr, weil eine ganze Menge Bier da berechnet wurde, die aber noch übrig war von früher
				
		# Verluste draufrechnen; relativ zum Preis
		asum = sum(personen.itervalues())
		for (p,psum) in personen.items():
			personen[p] += fehltGeld * (psum / asum)

		for (p,psum) in personen.items():
			print " ", p, ":", geld(psum)

		self.summe = sum(personen.itervalues())
		print "  Insgesamt:", geld(self.summe)

		if self.betragForChecking is None: raise Err, "'Betrag' wurde nicht in Abrechnung vom " + self.date + " angegeben"
		if abs(self.summe - self.betragForChecking) >= 0.01:
			raise Err, "Eingetragener Betrag " + geld(self.betragForChecking) + " weicht um " + geld(abs(self.summe - self.betragForChecking)) + " von ausgerechneter Summe ab in Abrechnung vom " + self.date

	def _parseGetraenke(self, data):
		getraenke = {}
		for e in [ re.match("^(\w+) ([0-9]+)$", e).groups() for e in re.split(" *, *", data) ]:
			if not e[0] in getraenkTypen: raise Err, "Getränk Typ " + e[0] + " unbekannt in '" + data + "' von Abrechnung vom " + self.date
			if e[0] in getraenke: raise Err, "Getränk Typ " + e[0] + " doppelt in '" + data + "' von Abrechnung vom " + self.date
			getraenke[e[0]] = int(e[1])			
		return getraenke
	
	def handle(self, l):
		# muss extra behandelt werden weil es nicht ins Muster passt
		if l.strip() == "noch da: -":
			if self.nochda: raise Err, "'noch da' wurde doppelt angegeben in Abrechnung " + self.date
			self.nochda = dict()
			return

		m = re.match("^Betrag: (?P<Betrag>[0-9,.]+) *$", l)
		if m:
			if self.betragForChecking: raise Err, "'Betrag' wurde doppelt angegeben in Abrechnung " + self.date
			self.betragForChecking = float(m.group("Betrag").replace(",","."))
			return
		
		abrechnRE = re.compile("^" +
			"(?P<type>[\w ]+): (?P<data>(\w+ [0-9]+, *)*\w+ [0-9]+)" +
			" *$", re.UNICODE)
		m = abrechnRE.match(l)
		if not m: raise Err, "Error, I don't understand (context Abrechnung): " + l

		Typ = m.group("type")
		Getraenke = self._parseGetraenke(m.group("data"))
		
		if Typ == "noch da":
			if self.nochda: raise Err, "'noch da' wurde doppelt angegeben in Abrechnung " + self.date
			self.nochda = Getraenke

		else:
			if Typ in self.personen: raise Err, "Person " + Typ + " doppelt angegeben in Abrechnung vom " + self.date + " in Zeile '" + l + "', bisherige Daten: " + repr(self.personen)
			self.personen[Typ] = Getraenke
			for (g,count) in Getraenke.items():
				stand.getraenke[g] -= count


bestellung = None
letzteBestellung = None
abrechnung = None

def finalizeLetzteBestellung():
	global letzteBestellung, stand
	if letzteBestellung: # bisher keine Abrechnung, daher letzteBestellung != None
		letzteBestellung.finalize()
		if letzteBestellung.pfandRueckgabe:
			raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Pfandrückgabe " + geld(letzteBestellung.pfandRueckgabe) + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
		if letzteBestellung.trinkgeld:
			raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Trinkgeld " + geld(letzteBestellung.trinkgeld) + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
		stand.handleBestellung(letzteBestellung)
		letzteBestellung = None


for l in f.readlines():
	l = l.strip()	
	if l.startswith("#"): continue
	if len(l) == 0: continue
	if l == ".":
		if bestellung:
			finalizeLetzteBestellung()
			letzteBestellung = bestellung
			bestellung = None
			
		elif abrechnung:
			if not letzteBestellung: raise Err, "Keine Bestellung zwischen letzter (" + abrechnung.date + ") und vorletzter Abrechnung"

			abrechnung.preFinalize()
			letzteBestellung.finalize()	
			abrechnung.finalize(letzteBestellung)
			stand.handleAbrechnung(abrechnung, letzteBestellung)
			stand.handleBestellung(letzteBestellung)
			letzteBestellung = None
			abrechnung = None
		else:
			raise Err, "Error, '.' only allowed in context (Abrechnung oder Bestellung)"

		context = None
		continue
	
	if bestellung:
		bestellung.handle(l)
	
	elif abrechnung:
		abrechnung.handle(l)
	
	else:
		bestellungTitleRE = re.compile("^Bestellung +(?P<date>.*): *$", re.IGNORECASE)
		b = bestellungTitleRE.match(l)
		if b:
			context = bestellung = Bestellung(b.group("date"))
			continue

		abrechnungTitleRE = re.compile("^Abrechnung +(?P<date>.*): *$", re.IGNORECASE)
		a = abrechnungTitleRE.match(l)
		if a:
			context = abrechnung = Abrechnung(a.group("date"))
			continue

		raise Err, "Error, I don't understand (no context): " + l
		
finalizeLetzteBestellung()
