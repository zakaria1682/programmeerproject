# ASSESSMENT.md

## Wat ik niet wil dat julie missen:

- **Rol- en rechtenmodel**  
  Ik heb een rol- en rechtenmodel gemaakt voor gebruikers (`user`, `author`, `admin`, `superadmin`) waarbij sommigen ook als decorator worden ingezet in de toekomst (nu nog niet).

- **Omzetting naar dialoog**
  Blogs en Opinies kunnen worden omgezet naar dialogen waarbij discussies mogelijk gemaakt worden in de vorm van mogelijkheid om te commenten op de opinies of blogs.

- **Dialoog- en commentsysteem met geneste structuur en votingsysteem**  
  Reacties kunnen genest worden (replies op replies), inclusief stemmen (upvote/downvote) en score-berekening, in het dialoog overzicht kunnen dialogen ook geupvote/gedownvote worden en worden dus uiteindelijk op populariteit gerangschikt.. 

- **Content-moderatie voor tekst én afbeeldingen**  
  Zowel tekst als afbeeldingen worden gecontroleerd op ongewenste inhoud via een LLM (chatGPT). Deze logica is herbruikbaar opgezet en consistent toegepast over het hele platform.

- **Beveiligde bestandsuploads**  
  Uploads worden gescheiden per context (profielafbeeldingen, blog-thumbnails, dialoog-thumbnails, editor-uploads) en gecontroleerd op type en grootte voordat ze permanent worden opgeslagen.

- **Gebruiksvriendelijke UX-details**  
  Flash-messages, validatie-feedback en hergebruik van formulieren bij fouten zijn bewust geïmplementeerd om de gebruikerservaring te verbeteren.

---

## Belangrijke ontwerpbeslissingen

### 1. LLM moderatie gecentraliseerd

**Waarom deze beslissing?**  
Ik had eerst de LLM los geimplementeerd overal en kwam erachter dat ik m best veel nodig zou hebben, dus die heb ik dan ook gecentraliseerd en herbruik ik waar nodig.

**Wat was minder handig aan eerdere ideeën?**  
De eerdere aanpak met losse code her en der werd al snel onoverzichtelijk en veel werk.

**Waarom is deze oplossing beter?**  
De huidige oplossing is herbruikbaar, uitbreidbaar en eenvoudig aan te passen. Ook achteraf blijkt dit een juiste keuze.

---






