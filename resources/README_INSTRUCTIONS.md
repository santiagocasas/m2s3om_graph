# Introduction



[OAI-PMH](https://en.wikipedia.org/wiki/Open_Archives_Initiative_Protocol_for_Metadata_Harvesting) is a **p**rotocol for **m**etadata **h**arvesting (PMH) published by the [Open Archives Initiative (OAI)](https://en.wikipedia.org/wiki/Open_Archives_Initiative). Libraries often provide an OAI endpoint which can be queried for the metadata of their records (like books, articles etc.).



# How this works:



* you take the url of the OAI endpoint, for example from the Alfred-Wegener-Institut: https://epic.awi.de/cgi/oai2

* you add `?verb=` and can now query for...

  * which metadata formats are supported by the endpoint by adding `ListMetadataFormats`: https://epic.awi.de/cgi/oai?verb=https://epic.awi.de/cgi/oai2?verb=ListMetadataFormats

  * list all records since March 2022 and use the dublin core format: https://epic.awi.de/cgi/oai2?verb=ListRecords&from=2022-03-01&metadataPrefix=oai_dc

  * ... (For an extensive List of possible queries, please see the [Datacite OAI-PMH Guide](https://support.datacite.org/docs/datacite-oai-pmh))



# Useful links:



* [OAI-PMH Documentation](https://www.openarchives.org/OAI/openarchivesprotocol.html)

* [Harvested OAI-PMH endpoints by Helmholtz Knowledge G](https://codebase.helmholtz.cloud/hmc/hmc-public/unhide/development/data_harvesting/-/blob/1.0.0-rc.9/config/OAIHarvester.config.yaml?ref_type=tags)raph

* [Datacite OAI-PMH Guide](https://support.datacite.org/docs/datacite-oai-pmh)



# Harvested OAI endpoints and their supported metadata formats



| Repository | OAI Endpoint | Metadata Prefixes |

|------------|--------------|-------------------|

| AWI | https://epic.awi.de/cgi/oai2 | awi, didl, mets, oai_bibl, oai_dc, oai_openaire, oai_pof4, rdf, uketd_dc |

| CISPA | https://publications.cispa.saarland/cgi/oai2 | didl, mets, oai_bibl, oai_dc, rdf, uketd_dc |

| DESY | https://bib-pubdb1.desy.de/oai2d | marcxml, openCost, xMetaDissPlus, epicur, oai_dc |

| DKFZ | https://inrepo02.dkfz.de/oai2d | marcxml, openCost, xMetaDissPlus, epicur, oai_dc |

| DLR | https://elib.dlr.de/cgi/oai2 | didl, mets, oai_bibl, oai_dc, oai_openaire, rdf, uketd_dc |

| DZNE | https://pub.dzne.de/oai2d | marcxml, openCost, xMetaDissPlus, epicur, oai_dc |

| FZJ | https://juser.fz-juelich.de/oai2d | marcxml, openCost, xMetaDissPlus, epicur, oai_dc |

| GEOMAR | https://oceanrep.geomar.de/cgi/oai2 | didl, mets, oai_bibl, oai_dc, oai_ep3, oai_geo, oai_openaire, oai_pof, rdf, uketd_dc |

| GSI | https://repository.gsi.de/oai2d | marcxml, openCost, xMetaDissPlus, epicur, oai_dc |

| HZB | https://www.helmholtz-berlin.de/pubbin/oai | oai_dc |

| HZDR | https://www.hzdr.de/publications/OAI-PMH | oai_dc |

| HZI | https://repository.helmholtz-hzi.de/oai/request | uketd_dc, qdc, didl, mods, ore, mets, oai_dc, rdf, marc, xoai, dim, etdms |

| UFZ | https://www.ufz.de/index.php?de=16406 | not found |

| HMGU | https://push-zb.helmholtz-munich.de/oai2/ | oai_dc |

| GFZ | https://gfzpublic.gfz-potsdam.de/oai/provider | escidoc, oai_dc |

| KIT | https://dbkit.bibliothek.kit.edu/oai/eva/ | oai_dc, epicur, oai_datacite |

| MDC | https://edoc.mdc-berlin.de/cgi/oai2 | didl, oai_bibl, oai_dc, uketd_dc |




