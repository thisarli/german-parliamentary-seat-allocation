# Imports

import pandas as pd
import numpy as np

# Functions

def sainte_lague(values, target):
  """
  Run an allocation based on the Sainte Lague / Webster method.
  
  Parameters
  ----------
  values: pandas.DataFrame with one column
      The initial data (e.g. population, votes) per index element, based on which allocation is done.
  target: float
      The total number of items (e.g. seats) to be  distributed.
  Returns
  -------
  allocations: pd.DataFrame
      Returns a DataFrame containing the Sainte Lague coonverted allocations per index element.
  """
  divisor=values.sum()/target
  allocations = round(values/divisor)
  if allocations.sum().squeeze() == target:
    return allocations
  elif allocations.sum().squeeze() < target:
    while allocations.sum().squeeze()<target:
      divisor*=0.999
      allocations = round(values/divisor)
    return allocations
  elif allocations.sum().squeeze()>target:
    while allocations.sum().squeeze()>target:
      divisor*=1.001
      allocations = round(values/divisor)
    return allocations

def get_wahlkreissitze_pro_partei_pro_bundesland(erststimmen_pro_partei_pro_wahlkreis):
  """
  Determine how many Wahlkreissitze each party gets per Bundesland, based on Erststimmen per Wahlkreis.
  In each Wahlkreis, the winning party is determined by simple majority.
  
  Parameters
  ----------
  erststimmen_pro_partei_pro_wahlkreis: pandas.DataFrame 
      Index: Wahlkreis. First Column: Bundesland. Remaining columns: number of Erststimmen for each party.
  Returns
  -------
  wahlkreissitze_pro_partei_pro_bundesland: pd.DataFrame
      Returns a DataFrame containing the number of won Wahlkreise per party per Bundesland.
      Index: party. Columns: Bundeslaender
  """
  interim=erststimmen_pro_partei_pro_wahlkreis.copy()
  interim['Sieger']=interim.iloc[:,1:].idxmax(axis=1) #determine winning party per Wahlkreis based on highest number of Erststimmen
  wahlkreissitze_pro_partei_pro_bundesland=interim.groupby(['Bundesland', 'Sieger']).size().reset_index(name='counts') #group by Bundesland
  wahlkreissitze_pro_partei_pro_bundesland = wahlkreissitze_pro_partei_pro_bundesland.pivot(index="Sieger", columns="Bundesland", values="counts").fillna(0.)
  return wahlkreissitze_pro_partei_pro_bundesland

def get_sitze_pro_bundesland(bevoelkerung_pro_bundesland,anzahl_sitze_parlament=598.0):
  """
  Determine initial number of parliamentary seats per Bundesland, based on the population per bundesland and the regular number of seats in parliament (default: 598).
  The allocation method is Sainte Lague.
  
  Parameters
  ----------
  bevoelkerung_pro_bundesland: pandas.DataFrame (one column)
      Index: Bundesland. Column: population
  Returns
  -------
  sitze_pro_bundesland: pd.DataFrame
      Returns a DataFrame containing the initial number of parliamentary seats per Bundesland (ignoring Überhangs-/Ausgleichsmandate).
      Index: Bundesland. Columns: Parliamentary seats
  """
  sitze_pro_bundesland=sainte_lague(bevoelkerung_pro_bundesland,anzahl_sitze_parlament)
  return sitze_pro_bundesland

def get_qualifizierte_parteien(erststimmen_pro_partei_pro_wahlkreis,zweitstimmen_pro_partei_pro_wahlkreis):
  """
  Determine the parties that get to participate in the allocation process.
  To participate in the allocation process, a parrty needs to get either at least 5% of Zweitstimmen at Bundesebene, or at least 3 Direktmandate.
  
  Parameters
  ----------
  erststimmen_pro_partei_pro_wahlkreis: pandas.DataFrame 
      Index: Wahlkreis. First Column: Bundesland. Remaining columns: number of Erststimmen for each party.
  zweitstimmen_pro_partei_pro_wahlkreis: pandas.DataFrame
      Index: Wahlkreis. First Column: Bundesland. Remaining columns: number of Erststimmen for each party.
  Returns
  -------
  qualifizierte_parteien: list
      Returns a list containing the parties that qualify for the allocation process in the Bundestag.
  """
  funf_prozent_berechnung=zweitstimmen_pro_partei_pro_wahlkreis.sum()[1:]/zweitstimmen_pro_partei_pro_wahlkreis.sum()[1:].sum() #zweitstimmen per party divided by total number of zweitstimmen
  parteien_mehr_als_funf_prozent=funf_prozent_berechnung.where(funf_prozent_berechnung.values>=0.05).dropna().index.tolist() #drop parties where % Zweitstimmen below 5% and get list of remaining parties
  wahlkreis_hurde_berechnung=get_wahlkreissitze_pro_partei_pro_bundesland(erststimmen_pro_partei_pro_wahlkreis).sum(axis=1) #calculate number of Wahlkreissitze per party on Bundesebene
  parteien_min_drei_wahlkreise=wahlkreis_hurde_berechnung.where(wahlkreis_hurde_berechnung.values>=3).dropna().index.tolist() #drop parties that don't have at least 3 Wahlkreissitze, and get list of remaining parties
  qualifizierte_parteien = list(set(parteien_mehr_als_funf_prozent+parteien_min_drei_wahlkreise)) #get union of the two lists
  return qualifizierte_parteien

def get_listensitze_pro_partei_pro_bundesland(sitze_pro_bundesland, zweitstimmen_pro_partei_pro_wahlkreis, qualifizierte_parteien):
  """
  Determine the seats each party gets per Bundesland based on Zweitstimmen.
  Only qualified parties can participate in this alocation step, which is based on Sainte Lague.
  
  Parameters
  ----------
  sitze_pro_bundesland: pd.DataFrame
      Index: Bundesland. Columns: Parliamentary seats
  zweitstimmen_pro_partei_pro_wahlkreis: pandas.DataFrame
      Index: Wahlkreis. First Column: Bundesland. Remaining columns: number of Erststimmen for each party.
  qualifizierte_parteien: list
  Returns
  -------
  listensitze_pro_partei_pro_bundesland: pd.DataFrame
      Returns  the seats each  qualified party gets, based on Zweitstimmen.
      Index: parties. Columns: Bundeslaender
  """
  zweitstimmen_pro_q_partei_pro_bundesland=zweitstimmen_pro_partei_pro_wahlkreis.groupby('Bundesland').sum()[qualifizierte_parteien] #find number of Zweitstimmen per qualified party per Bundesland
  d={}
  for i in sitze_pro_bundesland.transpose(): #for each Bundesland, determine Listensitze per party, allocated through Sainte Lague
    d[i]=sainte_lague(zweitstimmen_pro_q_partei_pro_bundesland.transpose()[i].to_frame(),sitze_pro_bundesland.transpose()[i].values[0])
  listensitze_pro_partei_pro_bundesland=pd.concat(d, axis=1).sum(axis=1, level=0) #concatenate the dictionary into a dataframe with parties as index and Bundeslaender as columns
  return listensitze_pro_partei_pro_bundesland

def get_mindestsitzzahlen_pro_partei_pro_bundesland(wahlkreissitze_pro_partei_pro_bundesland,listensitze_pro_partei_pro_bundesland):
  """
  Determine the minimum number of seats per party per Bundesland.
  This takes into account that a party cannot end up with fewer seats per Bundesland than that party has won in terms of Direktmandate (Erststimmen).
  
  Parameters
  ----------
  wahlkreissitze_pro_partei_pro_bundesland: pd.DataFrame
      Index: party. Columns: Bundeslaender
  listensitze_pro_partei_pro_bundesland: pd.DataFrame
      Index: parties. Columns: Bundeslaender
  Returns
  -------
  mindestsitzzahlen_pro_partei_pro_bundesland: pd.DataFrame
      Returns DataFrame with minimum number of seats per party per Bundesland, based on the max between the seats according to Zweitstimmen via Sainte Lague and Direktmandaten.
      Index: parties. Columns: Bundeslaender
  """
  mindestsitzzahlen_pro_partei_pro_bundesland = pd.concat([wahlkreissitze_pro_partei_pro_bundesland, listensitze_pro_partei_pro_bundesland]).max(level=0)
  return mindestsitzzahlen_pro_partei_pro_bundesland

def get_gesamtzahl_bundestagssitze_pro_partei(mindestsitzzahlen_pro_partei_pro_bundesland,zweitstimmen_pro_partei_pro_wahlkreis,qualifizierte_parteien):
  mindestsitzzahlen_pro_partei=mindestsitzzahlen_pro_partei_pro_bundesland.sum(axis=1).to_frame().sort_index()
  zweitstimmen_pro_q_partei=zweitstimmen_pro_partei_pro_wahlkreis.groupby('Bundesland').sum()[qualifizierte_parteien].sum().to_frame()
  divisor=zweitstimmen_pro_q_partei.sum()/mindestsitzzahlen_pro_partei.sum()
  allocations=round(zweitstimmen_pro_q_partei/divisor).sort_index()
  if ((allocations >= mindestsitzzahlen_pro_partei)*1).all()[0] == True:
    return allocations
  else:
    while ((allocations >= mindestsitzzahlen_pro_partei)*1).all()[0] == False:
      divisor*=0.9999
      allocations=round(zweitstimmen_pro_q_partei/divisor).sort_index()
    return allocations

def sainte_lague_final(values, minima, target):
  divisor=values.sum()/target
  allocations = round(values/divisor)
  interim = pd.concat([allocations, minima]).max(level=0)
  if interim.sum() == target:
    return interim
  elif interim.sum() < target:
    while interim.sum()<target:
      divisor*=0.999
      allocations = round(values/divisor)
      interim = pd.concat([allocations, minima]).max(level=0)
    return interim
  elif interim.sum()>target:
    while interim.sum()>target:
      divisor*=1.001
      allocations = round(values/divisor)
      interim = pd.concat([allocations, minima]).max(level=0)
    return interim

def get_sitze_pro_bundesland_pro_partei_final(zweitstimmen_pro_partei_pro_wahlkreis,qualifizierte_parteien,wahlkreissitze_pro_partei_pro_bundesland,gesamtzahl_bundestagssitze_pro_partei):
  zweitstimmen_pro_q_partei_pro_bundesland=zweitstimmen_pro_partei_pro_wahlkreis.groupby('Bundesland').sum()[qualifizierte_parteien]
  d={}
  for i in qualifizierte_parteien:
    d[i]=sainte_lague_final(zweitstimmen_pro_q_partei_pro_bundesland[i], wahlkreissitze_pro_partei_pro_bundesland.transpose()[i],gesamtzahl_bundestagssitze_pro_partei.transpose()[i][0])
  sitze_pro_bundesland_pro_partei_final= pd.concat(d, axis=1).sum(axis=1, level=0)
  return sitze_pro_bundesland_pro_partei_final

def run_bundestagssitz_verteilung(bevoelkerung_pro_bundesland,erststimmen_pro_partei_pro_wahlkreis,zweitstimmen_pro_partei_pro_wahlkreis):
  wahlkreissitze_pro_partei_pro_bundesland=get_wahlkreissitze_pro_partei_pro_bundesland(erststimmen_pro_partei_pro_wahlkreis)
  sitze_pro_bundesland=get_sitze_pro_bundesland(bevoelkerung_pro_bundesland,anzahl_sitze_parlament=598.0)
  qualifizierte_parteien=get_qualifizierte_parteien(erststimmen_pro_partei_pro_wahlkreis,zweitstimmen_pro_partei_pro_wahlkreis)
  listensitze_pro_partei_pro_bundesland=get_listensitze_pro_partei_pro_bundesland(sitze_pro_bundesland, zweitstimmen_pro_partei_pro_wahlkreis, qualifizierte_parteien)
  mindestsitzzahlen_pro_partei_pro_bundesland=get_mindestsitzzahlen_pro_partei_pro_bundesland(wahlkreissitze_pro_partei_pro_bundesland,listensitze_pro_partei_pro_bundesland)
  gesamtzahl_bundestagssitze_pro_partei=get_gesamtzahl_bundestagssitze_pro_partei(mindestsitzzahlen_pro_partei_pro_bundesland,zweitstimmen_pro_partei_pro_wahlkreis, qualifizierte_parteien)
  sitze_pro_bundesland_pro_partei_final=get_sitze_pro_bundesland_pro_partei_final(zweitstimmen_pro_partei_pro_wahlkreis,qualifizierte_parteien,wahlkreissitze_pro_partei_pro_bundesland,gesamtzahl_bundestagssitze_pro_partei)
  return sitze_pro_bundesland_pro_partei_final

# Load sample data

bevoelkerung_pro_bundesland = pd.read_csv('population_germany.csv')
bevoelkerung_pro_bundesland = bevoelkerung_pro_bundesland.set_index('Unnamed: 0')

erststimmen_pro_partei_pro_wahlkreis=pd.read_csv('erststimmen_pro_partei_pro_wahlkreis.csv')
erststimmen_pro_partei_pro_wahlkreis = erststimmen_pro_partei_pro_wahlkreis.set_index('Wahlkreis')

zweitstimmen_pro_partei_pro_wahlkreis=pd.read_csv('zweitstimmen_pro_partei_pro_wahlkreis.csv')
zweitstimmen_pro_partei_pro_wahlkreis = zweitstimmen_pro_partei_pro_wahlkreis.set_index('Wahlkreis')

# Run allocation

run_bundestagssitz_verteilung(bevoelkerung_pro_bundesland,erststimmen_pro_partei_pro_wahlkreis,zweitstimmen_pro_partei_pro_wahlkreis)
