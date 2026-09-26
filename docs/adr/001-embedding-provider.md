# ADR 001: Behåll lokal hybridrankning som standard

Datum: 2026-09-26

## Beslut

`EMBEDDING_PROVIDER=mock` behålls som produktionsstandard. Namnet är historiskt;
providern är en deterministisk lokal ord- och n-gramsignal som används tillsammans
med lexikal rankning, IDF, frasboost och avgränsade avsiktsregler.

## Underlag

Det versionskontrollerade facitet i `src/benchmarks/search_quality_data.py`
innehåller 22 vanliga svenska HR-frågor. Efter rankningsrättningarna gav den
levande Firestore-korpusen 22 av 22 rätt styrande paragraf som toppträff.

En extern embeddingprovider skulle kräva en hemlighet, återkommande kostnad och
full omindexering av alla länder. Det finns därför ingen verifierad kvalitetsvinst
som motiverar ett byte nu.

## Omprövning

Jämför OpenAI/Gemini mot samma facit och ett separat flerspråkigt facit innan ett
framtida byte. Byt bara om förbättringen är mätbar, och omindexera då hela korpusen
atomiskt eftersom vektorer från olika providers inte får blandas.
