#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import re
import math

dir = os.path.dirname(sys.argv[0])
f = open(dir + "/abrechnung.txt")

bestellungTitleRE = re.compile("^Bestellung +(?P<date>.*): *$", re.IGNORECASE)
abrechnungTitleRE = re.compile("^Abrechnung +(?P<date>.*): *$", re.IGNORECASE)

getraenkeBezahltRE = re.compile("^bezahlt: (?P<Betrag>[0-9,.]+) *$", re.UNICODE)
getraenkeTrinkgeldRE = re.compile("^Trinkgeld: (?P<Betrag>[0-9,.]+) *$", re.UNICODE)

getraenkRE = re.compile("^" +
	"(?P<Getraenk>[\w ]+) (?P<FlaschenAnzahl>\d+)x(?P<FlaschenInhalt>[0-9,.]+): *" +
	"(?P<KaestenAnzahl>[0-9,.]+) *\* *(?P<KastenPreis>[0-9,.]+)" +
	" *$", re.UNICODE)

abrechnRE = re.compile("^" +
	"(?P<type>[\w ]+): (?P<data>(\w+ [0-9]+, *)*\w+ [0-9]+)" +
	" *$", re.UNICODE)

class Err(Exception):
	def __init__(self, txt):
		self.txt = txt
	def __str__(self):
		# additional stuff for better readability
		return "\n-------------------------------------------\n" + self.txt

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

	def handleBestellung(self, best):
		if best.bezahlt:
			self.geldInKasse -= best.bezahlt + best.trinkgeld
			desc = "-" + geld(best.bezahlt).strip()
		else:
			self.rechnungNochOffen = best
			desc = "offen"

		for g in getraenkTypen:
			if g in best.preise:
				self.getraenkePreise[g] = best.preise[g]

		self.dump("Bestellung (" + desc + ")")
		
	def handleAbrechnung(self, abr, letzteBest):
		if self.rechnungNochOffen: raise Err, "kann Abrechnung nicht machen, wenn noch eine Rechnung offen steht; offen stehende Rechnung vom " + self.rechnungNochOffen.date
		self.geldInKasse += abr.summe
		self.dump("Abrechnung (+" + geld(abr.summe).strip() + ")")
		g = self.geldInKasse + letzteBest.pfandRueckgabe - letzteBest.trinkgeld
		print "  mit Pfandrückgabe (+" + geld(letzteBest.pfandRueckgabe).strip() + ") und Trinkgeld(-" + geld(letzteBest.trinkgeld).strip() + ") :", geld(g), "(~= -Wert der noch vorhandenen Flaschen)"
		
	def dump(self, desc):
		print "Geld in Kasse nach", desc, ":", geld(self.geldInKasse), " noch eine Rechnung offen" if self.rechnungNochOffen else ""
		
stand = Stand()

def wertVonGetraenken(getraenke):
	geld = 0.0
	for g in getraenkTypen:
		if g in getraenke:
			#print g, "da:", self.getraenke[g], "  preis:", self.getraenkePreise[g]
			geld += getraenke[g] * stand.getraenkePreise[g] 
	return geld



class Bestellung:
	def __init__(self, date):
		self.date = date
		self.getraenke = {}
		for g in getraenkTypen: self.getraenke[g] = 0
		self.preise = {}
		self.betrag = 0
		self.pfand = 0
		self.bezahlt = None
		self.trinkgeld = None
		self.pfandRueckgabe = None

	def finalize(self):
		for getraenkTyp in self.getraenke:
			stand.getraenke[getraenkTyp] += self.getraenke[getraenkTyp]

		print \
			"Bestellung", self.date, ":", \
			self.betrag, "€", \
			" Pfand:", self.pfand, "€", \
			" Summe:", self.betrag + self.pfand, "€"
		if self.bezahlt:
			if self.trinkgeld == None: raise Err, "Trinkgeld wurde in Bestellung vom " + self.date + " nicht angegeben"
			self.pfandRueckgabe = self.betrag + self.pfand - self.bezahlt
			print "  bezahlt:", geld(self.bezahlt).strip(), " Differenz (Pfandrückgabe):", geld(self.pfandRueckgabe).strip(), " Trinkgeld:", geld(self.trinkgeld).strip()
		else:
			print "  noch nicht bezahlt"
		
	def getraenkTyp(self, name):
		if "Apfelschorle" in name: return "A"
		if "Kastell" in name: return "Wasser"
		if "Cola" in name: return "Cola"
		if "Orange" in name: return "O"
		if "Bitburger" in name: return "Bier"
		raise Err, "Getränk " + name + " unbekannt!"

	def handle(self, l):
		m = getraenkeTrinkgeldRE.match(l)
		if m:
			self.trinkgeld = float(m.group("Betrag").replace(",","."))
			return

		m = getraenkeBezahltRE.match(l)
		if m:
			self.bezahlt = float(m.group("Betrag").replace(",","."))
			return
			
		m = getraenkRE.match(l)
		if not m: raise Err, "Error, I don't understand (context Bestellung): " + l
		
		Getraenk = m.group("Getraenk")
		GetraenkTyp = self.getraenkTyp(Getraenk)
		KastenPfand = 1.5
		FlaschenPfand = 0.15
		if Getraenk == "Kastell Apfelschorle": FlaschenPfand = 0.25 # sind PET flaschen
		if GetraenkTyp == "Bier": FlaschenPfand = 0.08

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
	
	def preFinalize(self):
		if self.nochda == None: raise Err, "'noch da' wurde nicht in Abrechnung vom " + self.date + " angegeben"

		# Verluste durch fehlende Flaschen ausrechnen
		#print "theoretisch noch da:", stand.getraenke, "; noch da:", self.nochda
		fehlt = {}
		fehltGeldFlaschen = 0
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
			#print p, ":", sum
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
		
			
	def parse(self, data):
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
		
		m = abrechnRE.match(l)
		if not m: raise Err, "Error, I don't understand (context Abrechnung): " + l

		Typ = m.group("type")
		Getraenke = self.parse(m.group("data"))
		
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


for l in f.readlines():
	l = l.strip()	
	if l.startswith("#"): continue
	if len(l) == 0: continue
	if l == ".":
		if bestellung:
			if letzteBestellung: # bisher keine Abrechnung, daher letzteBestellung != None
				letzteBestellung.finalize()	
				if letzteBestellung.pfandRueckgabe:
					raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Pfandrückgabe " + geld(letzteBestellung.pfandRueckgabe).strip() + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
				if letzteBestellung.trinkgeld:
					raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Trinkgeld " + geld(letzteBestellung.trinkgeld).strip() + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
				stand.handleBestellung(letzteBestellung)
				letzteBestellung = None
				
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
			
		continue
	
	if bestellung:
		bestellung.handle(l)
	
	elif abrechnung:
		abrechnung.handle(l)
	
	else:
		b = bestellungTitleRE.match(l)
		if b:
			bestellung = Bestellung(b.group("date"))
			continue
	
		a = abrechnungTitleRE.match(l)
		if a:
			abrechnung = Abrechnung(a.group("date"))
			continue

		raise Err, "Error, I don't understand (no context): " + l
		

if letzteBestellung:
	letzteBestellung.finalize()	
	if letzteBestellung.pfandRueckgabe:
		raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Pfandrückgabe " + geld(letzteBestellung.pfandRueckgabe).strip() + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
	if letzteBestellung.trinkgeld:
		raise Err, "Bestellung von " + letzteBestellung.date + " ohne nachfolgender Abrechnung, aber mit Trinkgeld " + geld(letzteBestellung.trinkgeld).strip() + " -> Verlust kann wegen fehlender Abrechnung nicht korrekt berechnet werden"
	stand.handleBestellung(letzteBestellung)
	letzteBestellung = None
