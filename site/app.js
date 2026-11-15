/* Market Desk Reborn — real-data-only UI, no third-party JS packages. */
'use strict';
const $ = (id) => document.getElementById(id);
const escapeHtml = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DEFAULT_STOCKS = ['AAPL','NVDA','MSFT','GOOGL','AMZN','META','TSLA','AMD','PLTR','JPM','KO','DIS','NFLX','BA','TSM','TTWO'];
const STOCK_NAMES = {TTWO:'Take-Two Interactive',AAPL:'Apple',NVDA:'NVIDIA',MSFT:'Microsoft',GOOGL:'Alphabet',AMZN:'Amazon',META:'Meta Platforms',TSLA:'Tesla',AMD:'AMD',PLTR:'Palantir',JPM:'JPMorgan',KO:'Coca-Cola',DIS:'Disney',NFLX:'Netflix',BA:'Boeing',TSM:'Taiwan Semiconductor','BRK.B':'Berkshire Hathaway',V:'Visa',MA:'Mastercard',WMT:'Walmart',INTC:'Intel'};
// Listing symbols checked against Nasdaq symbol directories on 3 November 2026.
const STOCK_DIRECTORY = Object.freeze([{"symbol":"AAPL","name":"Apple","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Apple Inc. - Common Stock","depositary":false},{"symbol":"ABBV","name":"AbbVie Inc.","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"AbbVie Inc. Common Stock","depositary":false},{"symbol":"ABNB","name":"Airbnb, Inc.","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"Airbnb, Inc. - Class A Common Stock","depositary":false},{"symbol":"ABT","name":"Abbott Laboratories","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Abbott Laboratories Common Stock","depositary":false},{"symbol":"ACN","name":"Accenture plc","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"Accenture plc Class A Ordinary Shares (Ireland)","depositary":false},{"symbol":"ADBE","name":"Adobe Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Adobe Inc. - Common Stock","depositary":false},{"symbol":"ADI","name":"Analog Devices, Inc.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Analog Devices, Inc. - Common Stock","depositary":false},{"symbol":"AEP","name":"American Electric Power Company, Inc.","category":"Utilities","exchange":"Nasdaq","currency":"USD","listingName":"American Electric Power Company, Inc. - Common Stock","depositary":false},{"symbol":"AIG","name":"American International Group, Inc. New","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"American International Group, Inc. New Common Stock","depositary":false},{"symbol":"ALAB","name":"Astera Labs, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Astera Labs, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ALL","name":"Allstate Corporation (The)","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Allstate Corporation (The) Common Stock","depositary":false},{"symbol":"AMAT","name":"Applied Materials, Inc.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Applied Materials, Inc. - Common Stock","depositary":false},{"symbol":"AMD","name":"Advanced Micro Devices, Inc.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Advanced Micro Devices, Inc. - Common Stock","depositary":false},{"symbol":"AMGN","name":"Amgen Inc.","category":"Healthcare","exchange":"Nasdaq","currency":"USD","listingName":"Amgen Inc. - Common Stock","depositary":false},{"symbol":"AMT","name":"American Tower Corporation (REIT)","category":"Property","exchange":"NYSE","currency":"USD","listingName":"American Tower Corporation (REIT) Common Stock","depositary":false},{"symbol":"AMZN","name":"Amazon","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"Amazon.com, Inc. - Common Stock","depositary":false},{"symbol":"ANET","name":"Arista Networks, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Arista Networks, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"AON","name":"Aon plc Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Aon plc Class A Ordinary Shares (Ireland)","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"APD","name":"Air Products and Chemicals, Inc.","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Air Products and Chemicals, Inc. Common Stock","depositary":false},{"symbol":"APLD","name":"Applied Digital Corporation","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Applied Digital Corporation - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"APO","name":"Apollo Global Management, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Apollo Global Management, Inc. (New) Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"APP","name":"Applovin Corporation","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Applovin Corporation - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ARM","name":"Arm Holdings plc","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Arm Holdings plc - American Depositary Shares","depositary":true},{"symbol":"ASML","name":"ASML Holding N.V.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"ASML Holding N.V. - New York Registry Shares","depositary":false},{"symbol":"ASTS","name":"AST SpaceMobile, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"AST SpaceMobile, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"AVGO","name":"Broadcom Inc.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Broadcom Inc. - Common Stock","depositary":false},{"symbol":"AWK","name":"American Water Works Company, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"American Water Works Company, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"AXP","name":"American Express Company","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"American Express Company Common Stock","depositary":false},{"symbol":"BA","name":"Boeing Company (The)","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Boeing Company (The) Common Stock","depositary":false},{"symbol":"BAC","name":"Bank of America Corporation","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Bank of America Corporation Common Stock","depositary":false},{"symbol":"BIDU","name":"Baidu, Inc. - American Depositary Shares, each representing 8 ordinary share","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Baidu, Inc. - American Depositary Shares, each representing 8 ordinary share","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"BILL","name":"BILL Holdings, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"BILL Holdings, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"BKNG","name":"Booking Holdings Inc.","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Booking Holdings Inc. - Common Stock","depositary":false},{"symbol":"BLK","name":"BlackRock, Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"BlackRock, Inc. Common Stock","depositary":false},{"symbol":"BMRN","name":"BioMarin Pharmaceutical Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"BioMarin Pharmaceutical Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"BMY","name":"Bristol-Myers Squibb Company","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Bristol-Myers Squibb Company Common Stock","depositary":false},{"symbol":"BNTX","name":"BioNTech SE - American Depositary Shares","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"BioNTech SE - American Depositary Shares","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"BRK.B","name":"Berkshire Hathaway (Class B)","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Berkshire Hathaway Inc. New Common Stock","depositary":false},{"symbol":"BROS","name":"Dutch Bros Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Dutch Bros Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"BSX","name":"Boston Scientific Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Boston Scientific Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"BX","name":"Blackstone Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Blackstone Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"C","name":"Citigroup, Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Citigroup, Inc. Common Stock","depositary":false},{"symbol":"CART","name":"Maplebear Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Maplebear Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CAT","name":"Caterpillar, Inc.","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Caterpillar, Inc. Common Stock","depositary":false},{"symbol":"CAVA","name":"CAVA Group, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"CAVA Group, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CB","name":"Chubb Limited","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Chubb Limited  Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CBOE","name":"Cboe Global Markets, Inc.","category":"More US listings","exchange":"Cboe BZX","currency":"USD","listingName":"Cboe Global Markets, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CCI","name":"Crown Castle Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Crown Castle Inc. Common Stock","depositary":false},{"symbol":"CDNS","name":"Cadence Design Systems, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Cadence Design Systems, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CEG","name":"Constellation Energy Corporation","category":"Energy","exchange":"Nasdaq","currency":"USD","listingName":"Constellation Energy Corporation - Common Stock When-Issued","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CELH","name":"Celsius Holdings, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Celsius Holdings, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CFG","name":"Citizens Financial Group, Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Citizens Financial Group, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CHTR","name":"Charter Communications, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Charter Communications, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CI","name":"The Cigna Group","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"The Cigna Group Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CIEN","name":"Ciena Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Ciena Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CIFR","name":"Cipher Digital Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Cipher Digital Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CL","name":"Colgate-Palmolive Company","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Colgate-Palmolive Company Common Stock","depositary":false},{"symbol":"CLS","name":"Celestica, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Celestica, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CLSK","name":"CleanSpark, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"CleanSpark, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CMCSA","name":"Comcast Corporation","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Comcast Corporation - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CME","name":"CME Group Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"CME Group Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CMG","name":"Chipotle Mexican Grill, Inc.","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Chipotle Mexican Grill, Inc. Common Stock","depositary":false},{"symbol":"COHR","name":"Coherent Corp.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Coherent Corp. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"COIN","name":"Coinbase Global, Inc.","category":"Banking & finance","exchange":"Nasdaq","currency":"USD","listingName":"Coinbase Global, Inc. - Class A Common Stock","depositary":false},{"symbol":"COP","name":"ConocoPhillips","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"ConocoPhillips Common Stock","depositary":false},{"symbol":"COR","name":"Cencora, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Cencora, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CORZ","name":"Core Scientific, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Core Scientific, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"COST","name":"Costco Wholesale Corporation","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Costco Wholesale Corporation - Common Stock","depositary":false},{"symbol":"CPNG","name":"Coupang, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Coupang, Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"CRDO","name":"Credo Technology Group Holding Ltd","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Credo Technology Group Holding Ltd - Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"CRM","name":"Salesforce, Inc.","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"Salesforce, Inc. Common Stock","depositary":false},{"symbol":"CRWD","name":"CrowdStrike Holdings, Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"CrowdStrike Holdings, Inc. - Class A Common Stock","depositary":false},{"symbol":"CSX","name":"CSX Corporation","category":"Industry & transport","exchange":"Nasdaq","currency":"USD","listingName":"CSX Corporation - Common Stock","depositary":false},{"symbol":"CVS","name":"CVS Health Corporation","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"CVS Health Corporation Common Stock","depositary":false},{"symbol":"CVX","name":"Chevron Corporation","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Chevron Corporation Common Stock","depositary":false},{"symbol":"D","name":"Dominion Energy, Inc.","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"Dominion Energy, Inc. Common Stock","depositary":false},{"symbol":"DASH","name":"DoorDash, Inc.","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"DoorDash, Inc. - Common Stock","depositary":false},{"symbol":"DD","name":"DuPont de Nemours, Inc.","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"DuPont de Nemours, Inc. Common Stock","depositary":false},{"symbol":"DDOG","name":"Datadog, Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Datadog, Inc. - Class A Common Stock","depositary":false},{"symbol":"DE","name":"Deere & Company","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Deere & Company Common Stock","depositary":false},{"symbol":"DHR","name":"Danaher Corporation","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Danaher Corporation Common Stock","depositary":false},{"symbol":"DIS","name":"Walt Disney Company (The)","category":"Internet & media","exchange":"NYSE","currency":"USD","listingName":"Walt Disney Company (The) Common Stock","depositary":false},{"symbol":"DKNG","name":"DraftKings Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"DraftKings Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"DLR","name":"Digital Realty Trust, Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Digital Realty Trust, Inc. Common Stock","depositary":false},{"symbol":"DOCN","name":"DigitalOcean Holdings, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"DigitalOcean Holdings, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"DOW","name":"Dow Inc.","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Dow Inc. Common Stock","depositary":false},{"symbol":"DPZ","name":"Domino's Pizza Inc","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Domino's Pizza Inc - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"DUK","name":"Duke Energy Corporation (Holding Company)","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"Duke Energy Corporation (Holding Company) Common Stock","depositary":false},{"symbol":"DUOL","name":"Duolingo, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Duolingo, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"EBAY","name":"eBay Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"eBay Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ECL","name":"Ecolab Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Ecolab Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ED","name":"Consolidated Edison, Inc.","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"Consolidated Edison, Inc. Common Stock","depositary":false},{"symbol":"EL","name":"Estee Lauder Companies, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Estee Lauder Companies, Inc. (The) Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ELV","name":"Elevance Health, Inc.","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Elevance Health, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"EMR","name":"Emerson Electric Company","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Emerson Electric Company Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ENPH","name":"Enphase Energy, Inc.","category":"Energy","exchange":"Nasdaq","currency":"USD","listingName":"Enphase Energy, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"EOG","name":"EOG Resources, Inc.","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"EOG Resources, Inc. Common Stock","depositary":false},{"symbol":"EQIX","name":"Equinix, Inc.","category":"Property","exchange":"Nasdaq","currency":"USD","listingName":"Equinix, Inc. - Common Stock","depositary":false},{"symbol":"ETN","name":"Eaton Corporation, PLC","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Eaton Corporation, PLC Ordinary Shares","depositary":false},{"symbol":"ETR","name":"Entergy Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Entergy Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ETSY","name":"Etsy, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Etsy, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"EW","name":"Edwards Lifesciences Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Edwards Lifesciences Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"EXC","name":"Exelon Corporation","category":"Utilities","exchange":"Nasdaq","currency":"USD","listingName":"Exelon Corporation - Common Stock","depositary":false},{"symbol":"F","name":"Ford Motor Company","category":"Cars","exchange":"NYSE","currency":"USD","listingName":"Ford Motor Company Common Stock","depositary":false},{"symbol":"FCX","name":"Freeport-McMoRan, Inc.","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Freeport-McMoRan, Inc. Common Stock","depositary":false},{"symbol":"FDX","name":"FedEx Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"FedEx Corporation Common Stock","depositary":false},{"symbol":"FICO","name":"Fair Isaac Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Fair Isaac Corporation Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"FIX","name":"Comfort Systems USA, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Comfort Systems USA, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"FOX","name":"Fox Corporation","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Fox Corporation - Class B Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"FSLR","name":"First Solar, Inc.","category":"Energy","exchange":"Nasdaq","currency":"USD","listingName":"First Solar, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"FTAI","name":"FTAI Aviation Ltd.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"FTAI Aviation Ltd. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"FTNT","name":"Fortinet, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Fortinet, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"GD","name":"General Dynamics Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"General Dynamics Corporation Common Stock","depositary":false},{"symbol":"GDDY","name":"GoDaddy Inc. Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"GoDaddy Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"GE","name":"GE Aerospace","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"GE Aerospace Common Stock","depositary":false},{"symbol":"GEV","name":"GE Vernova","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"GE Vernova Inc. Common Stock","depositary":false},{"symbol":"GILD","name":"Gilead Sciences, Inc.","category":"Healthcare","exchange":"Nasdaq","currency":"USD","listingName":"Gilead Sciences, Inc. - Common Stock","depositary":false},{"symbol":"GIS","name":"General Mills, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"General Mills, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"GLW","name":"Corning Incorporated","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Corning Incorporated Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"GM","name":"General Motors Company","category":"Cars","exchange":"NYSE","currency":"USD","listingName":"General Motors Company Common Stock","depositary":false},{"symbol":"GOOGL","name":"Alphabet (Google)","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"Alphabet Inc. - Class A Common Stock","depositary":false},{"symbol":"GRAB","name":"Grab Holdings Limited","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Grab Holdings Limited - Class A Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"GS","name":"Goldman Sachs Group, Inc. (The)","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Goldman Sachs Group, Inc. (The) Common Stock","depositary":false},{"symbol":"GTLB","name":"GitLab Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"GitLab Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"HCA","name":"HCA Healthcare, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"HCA Healthcare, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HD","name":"Home Depot, Inc. (The)","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Home Depot, Inc. (The) Common Stock","depositary":false},{"symbol":"HIMS","name":"Hims & Hers Health, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Hims & Hers Health, Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HLT","name":"Hilton Worldwide Holdings Inc.","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Hilton Worldwide Holdings Inc. Common Stock","depositary":false},{"symbol":"HMC","name":"Honda Motor Company, Ltd.","category":"Cars","exchange":"NYSE","currency":"USD","listingName":"Honda Motor Company, Ltd. Common Stock","depositary":false},{"symbol":"HON","name":"Honeywell International Inc.","category":"Industry & transport","exchange":"Nasdaq","currency":"USD","listingName":"Honeywell International Inc. - Common Stock","depositary":false},{"symbol":"HOOD","name":"Robinhood Markets, Inc.","category":"Banking & finance","exchange":"Nasdaq","currency":"USD","listingName":"Robinhood Markets, Inc. - Class A Common Stock","depositary":false},{"symbol":"HR","name":"Healthcare Realty Trust Incorporated","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Healthcare Realty Trust Incorporated Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HSY","name":"The Hershey Company","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"The Hershey Company Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HUBS","name":"HubSpot, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"HubSpot, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HUM","name":"Humana Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Humana Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"HUT","name":"Hut 8 Corp.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Hut 8 Corp. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"IBM","name":"International Business Machines Corporation","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"International Business Machines Corporation Common Stock","depositary":false},{"symbol":"ICE","name":"Intercontinental Exchange Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Intercontinental Exchange Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"INTC","name":"Intel Corporation","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Intel Corporation - Common Stock","depositary":false},{"symbol":"INTU","name":"Intuit Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Intuit Inc. - Common Stock","depositary":false},{"symbol":"IONQ","name":"IonQ, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"IonQ, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"IOT","name":"Samsara Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Samsara Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"IREN","name":"IREN Limited","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"IREN Limited - Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ISRG","name":"Intuitive Surgical, Inc.","category":"Healthcare","exchange":"Nasdaq","currency":"USD","listingName":"Intuitive Surgical, Inc. - Common Stock","depositary":false},{"symbol":"ITW","name":"Illinois Tool Works Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Illinois Tool Works Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"JD","name":"JD.com, Inc. - American Depositary Shares","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"JD.com, Inc. - American Depositary Shares","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"JNJ","name":"Johnson & Johnson","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Johnson & Johnson Common Stock","depositary":false},{"symbol":"JPM","name":"JPMorgan Chase","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"JP Morgan Chase & Co. Common Stock","depositary":false},{"symbol":"KHC","name":"The Kraft Heinz Company","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"The Kraft Heinz Company Common Stock","depositary":false},{"symbol":"KKR","name":"KKR & Co. Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"KKR & Co. Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"KLAC","name":"KLA Corporation","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"KLA Corporation  - Common Stock","depositary":false},{"symbol":"KMB","name":"Kimberly-Clark Corporation","category":"Food & household","exchange":"Nasdaq","currency":"USD","listingName":"Kimberly-Clark Corporation - Common Stock","depositary":false},{"symbol":"KO","name":"Coca-Cola","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Coca-Cola Company (The) Common Stock","depositary":false},{"symbol":"LCID","name":"Lucid Group, Inc.","category":"Cars","exchange":"Nasdaq","currency":"USD","listingName":"Lucid Group, Inc. - Common Stock","depositary":false},{"symbol":"LDOS","name":"Leidos Holdings, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Leidos Holdings, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"LI","name":"Li Auto Inc. - American Depositary Shares","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Li Auto Inc. - American Depositary Shares","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"LIN","name":"Linde plc","category":"Materials","exchange":"Nasdaq","currency":"USD","listingName":"Linde plc - Ordinary Shares","depositary":false},{"symbol":"LITE","name":"Lumentum Holdings Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Lumentum Holdings Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"LLY","name":"Eli Lilly","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Eli Lilly and Company Common Stock","depositary":false},{"symbol":"LMT","name":"Lockheed Martin Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Lockheed Martin Corporation Common Stock","depositary":false},{"symbol":"LNG","name":"Cheniere Energy, Inc.","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Cheniere Energy, Inc. Common Stock","depositary":false},{"symbol":"LOW","name":"Lowe's Companies, Inc.","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Lowe's Companies, Inc. Common Stock","depositary":false},{"symbol":"LRCX","name":"Lam Research Corporation","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Lam Research Corporation - Common Stock","depositary":false},{"symbol":"LULU","name":"lululemon athletica inc.","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"lululemon athletica inc. - Common Stock","depositary":false},{"symbol":"LVS","name":"Las Vegas Sands Corp.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Las Vegas Sands Corp. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"LYV","name":"Live Nation Entertainment, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Live Nation Entertainment, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MA","name":"Mastercard Incorporated","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Mastercard Incorporated Common Stock","depositary":false},{"symbol":"MAR","name":"Marriott International","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Marriott International - Class A Common Stock","depositary":false},{"symbol":"MARA","name":"MARA Holdings, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"MARA Holdings, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MCD","name":"McDonald's Corporation","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"McDonald's Corporation Common Stock","depositary":false},{"symbol":"MCHP","name":"Microchip Technology Incorporated","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Microchip Technology Incorporated - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MCK","name":"McKesson Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"McKesson Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MCO","name":"Moody's Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Moody's Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MDB","name":"MongoDB, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"MongoDB, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MDLZ","name":"Mondelez International, Inc.","category":"Food & household","exchange":"Nasdaq","currency":"USD","listingName":"Mondelez International, Inc. - Class A Common Stock","depositary":false},{"symbol":"MELI","name":"MercadoLibre, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"MercadoLibre, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MET","name":"MetLife, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"MetLife, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"META","name":"Meta Platforms","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"Meta Platforms, Inc. - Class A Common Stock","depositary":false},{"symbol":"MGM","name":"MGM Resorts International","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"MGM Resorts International Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MO","name":"Altria Group, Inc.","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Altria Group, Inc.","depositary":false},{"symbol":"MOH","name":"Molina Healthcare Inc","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Molina Healthcare Inc Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MPC","name":"Marathon Petroleum Corporation","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Marathon Petroleum Corporation Common Stock","depositary":false},{"symbol":"MRK","name":"Merck & Company, Inc.","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Merck & Company, Inc. Common Stock (new)","depositary":false},{"symbol":"MRNA","name":"Moderna, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Moderna, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MRVL","name":"Marvell Technology, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Marvell Technology, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MS","name":"Morgan Stanley","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Morgan Stanley Common Stock","depositary":false},{"symbol":"MSCI","name":"MSCI Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"MSCI Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"MSFT","name":"Microsoft","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Microsoft Corporation - Common Stock","depositary":false},{"symbol":"MSTR","name":"Strategy Inc","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Strategy Inc - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MTCH","name":"Match Group, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Match Group, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"MU","name":"Micron Technology, Inc.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Micron Technology, Inc. - Common Stock","depositary":false},{"symbol":"NBIS","name":"Nebius Group N.V.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Nebius Group N.V. - Class A Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"NEE","name":"NextEra Energy, Inc.","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"NextEra Energy, Inc. Common Stock","depositary":false},{"symbol":"NEM","name":"Newmont Corporation","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Newmont Corporation","depositary":false},{"symbol":"NET","name":"Cloudflare, Inc.","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"Cloudflare, Inc. Class A Common Stock","depositary":false},{"symbol":"NFLX","name":"Netflix, Inc.","category":"Internet & media","exchange":"Nasdaq","currency":"USD","listingName":"Netflix, Inc. - Common Stock","depositary":false},{"symbol":"NIO","name":"NIO Inc. American depositary shares, each representing one Class A ordinary shar","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"NIO Inc. American depositary shares, each  representing one Class A ordinary share","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"NKE","name":"Nike, Inc.","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Nike, Inc. Common Stock","depositary":false},{"symbol":"NOC","name":"Northrop Grumman Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Northrop Grumman Corporation Common Stock","depositary":false},{"symbol":"NOW","name":"ServiceNow, Inc.","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"ServiceNow, Inc. Common Stock","depositary":false},{"symbol":"NRG","name":"NRG Energy, Inc.","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"NRG Energy, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"NTNX","name":"Nutanix, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Nutanix, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"NTRA","name":"Natera, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Natera, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"NU","name":"Nu Holdings Ltd. Ordinary Shares","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Nu Holdings Ltd. Class A Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"NUE","name":"Nucor Corporation","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Nucor Corporation Common Stock","depositary":false},{"symbol":"NVDA","name":"NVIDIA","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"NVIDIA Corporation - Common Stock","depositary":false},{"symbol":"NXPI","name":"NXP Semiconductors N.V.","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"NXP Semiconductors N.V. - Common Stock","depositary":false},{"symbol":"O","name":"Realty Income Corporation","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Realty Income Corporation Common Stock","depositary":false},{"symbol":"OKLO","name":"Oklo Inc. common stock","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Oklo Inc. Class A common stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ON","name":"ON Semiconductor Corporation","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"ON Semiconductor Corporation - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ONON","name":"On Holding AG Ordinary Shares","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"On Holding AG Class A Ordinary Shares","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ORCL","name":"Oracle Corporation","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"Oracle Corporation Common Stock","depositary":false},{"symbol":"OXY","name":"Occidental Petroleum Corporation","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Occidental Petroleum Corporation Common Stock","depositary":false},{"symbol":"PANW","name":"Palo Alto Networks, Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Palo Alto Networks, Inc. - Common Stock","depositary":false},{"symbol":"PARA","name":"Parabolic Technologies, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Parabolic Technologies, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"PCAR","name":"PACCAR Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"PACCAR Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"PDD","name":"PDD Holdings Inc. - American Depositary Shares","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"PDD Holdings Inc. - American Depositary Shares","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"PEP","name":"PepsiCo, Inc.","category":"Food & household","exchange":"Nasdaq","currency":"USD","listingName":"PepsiCo, Inc. - Common Stock","depositary":false},{"symbol":"PFE","name":"Pfizer, Inc.","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Pfizer, Inc. Common Stock","depositary":false},{"symbol":"PG","name":"Procter & Gamble","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Procter & Gamble Company (The) Common Stock","depositary":false},{"symbol":"PGR","name":"Progressive Corporation (The)","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Progressive Corporation (The) Common Stock","depositary":false},{"symbol":"PH","name":"Parker-Hannifin Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Parker-Hannifin Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"PINS","name":"Pinterest, Inc.","category":"Internet & media","exchange":"NYSE","currency":"USD","listingName":"Pinterest, Inc. Class A Common Stock","depositary":false},{"symbol":"PL","name":"Planet Labs PBC","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Planet Labs PBC Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"PLD","name":"Prologis, Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Prologis, Inc. Common Stock","depositary":false},{"symbol":"PLTR","name":"Palantir Technologies Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Palantir Technologies Inc. - Class A Common Stock","depositary":false},{"symbol":"PM","name":"Philip Morris International Inc","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Philip Morris International Inc Common Stock","depositary":false},{"symbol":"PNC","name":"PNC Financial Services Group, Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"PNC Financial Services Group, Inc. (The) Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"PRU","name":"Prudential Financial, Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Prudential Financial, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"PSA","name":"Public Storage","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Public Storage Common Stock","depositary":false},{"symbol":"PSX","name":"Phillips 66","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Phillips 66 Common Stock","depositary":false},{"symbol":"PYPL","name":"PayPal Holdings, Inc.","category":"Banking & finance","exchange":"Nasdaq","currency":"USD","listingName":"PayPal Holdings, Inc. - Common Stock","depositary":false},{"symbol":"QCOM","name":"QUALCOMM Incorporated","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"QUALCOMM Incorporated - Common Stock","depositary":false},{"symbol":"RBLX","name":"Roblox","category":"Games","exchange":"NYSE","currency":"USD","listingName":"Roblox Corporation Class A Common Stock","depositary":false},{"symbol":"RBRK","name":"Rubrik, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Rubrik, Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"RCL","name":"Royal Caribbean Cruises Ltd.","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Royal Caribbean Cruises Ltd. Common Stock","depositary":false},{"symbol":"RDDT","name":"Reddit, Inc.","category":"Internet & media","exchange":"NYSE","currency":"USD","listingName":"Reddit, Inc. Class A Common Stock","depositary":false},{"symbol":"REGN","name":"Regeneron Pharmaceuticals, Inc.","category":"Healthcare","exchange":"Nasdaq","currency":"USD","listingName":"Regeneron Pharmaceuticals, Inc. - Common Stock","depositary":false},{"symbol":"RF","name":"Regions Financial Corporation","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Regions Financial Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"RIOT","name":"Riot Platforms, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Riot Platforms, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"RIVN","name":"Rivian Automotive, Inc.","category":"Cars","exchange":"Nasdaq","currency":"USD","listingName":"Rivian Automotive, Inc. - Class A Common Stock","depositary":false},{"symbol":"RKLB","name":"Rocket Lab Corporation","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Rocket Lab Corporation - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"ROST","name":"Ross Stores, Inc.","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Ross Stores, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"RTX","name":"RTX Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"RTX Corporation Common Stock","depositary":false},{"symbol":"RXRX","name":"Recursion Pharmaceuticals, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Recursion Pharmaceuticals, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SBUX","name":"Starbucks Corporation","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Starbucks Corporation - Common Stock","depositary":false},{"symbol":"SCHW","name":"Charles Schwab Corporation (The)","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Charles Schwab Corporation (The) Common Stock","depositary":false},{"symbol":"SE","name":"Sea Limited American Depositary Shares, each representing one Class A Ordinary S","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Sea Limited American Depositary Shares, each representing one Class A Ordinary Share","depositary":true,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"SHOP","name":"Shopify Inc.","category":"Technology","exchange":"Nasdaq","currency":"USD","listingName":"Shopify Inc. - Class A Subordinate Voting Shares","depositary":false},{"symbol":"SHW","name":"Sherwin-Williams Company (The)","category":"Materials","exchange":"NYSE","currency":"USD","listingName":"Sherwin-Williams Company (The) Common Stock","depositary":false},{"symbol":"SIRI","name":"SiriusXM Holdings Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"SiriusXM Holdings Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SLB","name":"SLB Limited Common Shares","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"SLB Limited Common Shares","depositary":false},{"symbol":"SMCI","name":"Super Micro Computer, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Super Micro Computer, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SMR","name":"NuScale Power Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"NuScale Power Corporation Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"SNAP","name":"Snap Inc. Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Snap Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"SNOW","name":"Snowflake Inc.","category":"Technology","exchange":"NYSE","currency":"USD","listingName":"Snowflake Inc. Common Stock","depositary":false},{"symbol":"SNPS","name":"Synopsys, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Synopsys, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SO","name":"Southern Company (The)","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"Southern Company (The) Common Stock","depositary":false},{"symbol":"SOFI","name":"SoFi Technologies, Inc. ","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"SoFi Technologies, Inc.  - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SONY","name":"Sony Group","category":"Games","exchange":"NYSE","currency":"USD","listingName":"Sony Group Corporation American Depositary Shares","depositary":true},{"symbol":"SOUN","name":"SoundHound AI, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"SoundHound AI, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"SPG","name":"Simon Property Group, Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Simon Property Group, Inc. Common Stock","depositary":false},{"symbol":"SPGI","name":"S&P Global Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"S&P Global Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"SPOT","name":"Spotify Technology S.A.","category":"Internet & media","exchange":"NYSE","currency":"USD","listingName":"Spotify Technology S.A. Ordinary Shares","depositary":false},{"symbol":"SRE","name":"DBA Sempra","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"DBA Sempra Common Stock","depositary":false},{"symbol":"STT","name":"State Street Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"State Street Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"STZ","name":"Constellation Brands, Inc.","category":"Food & household","exchange":"NYSE","currency":"USD","listingName":"Constellation Brands, Inc. Common Stock","depositary":false},{"symbol":"SYK","name":"Stryker Corporation","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Stryker Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"T","name":"AT&T Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"AT&T Inc.","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"TEAM","name":"Atlassian Corporation ","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Atlassian Corporation  - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"TEM","name":"Tempus AI, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Tempus AI, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"TFC","name":"Truist Financial Corporation","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Truist Financial Corporation Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"TGT","name":"Target Corporation","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"Target Corporation Common Stock","depositary":false},{"symbol":"TJX","name":"TJX Companies, Inc. (The)","category":"Shops & travel","exchange":"NYSE","currency":"USD","listingName":"TJX Companies, Inc. (The) Common Stock","depositary":false},{"symbol":"TM","name":"Toyota Motor Corporation","category":"Cars","exchange":"NYSE","currency":"USD","listingName":"Toyota Motor Corporation Common Stock","depositary":false},{"symbol":"TMO","name":"Thermo Fisher Scientific Inc","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"Thermo Fisher Scientific Inc Common Stock","depositary":false},{"symbol":"TMUS","name":"T-Mobile US, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"T-Mobile US, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"TOST","name":"Toast, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Toast, Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"TRV","name":"The Travelers Companies, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"The Travelers Companies, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"TSLA","name":"Tesla, Inc.","category":"Cars","exchange":"Nasdaq","currency":"USD","listingName":"Tesla, Inc.  - Common Stock","depositary":false},{"symbol":"TSM","name":"Taiwan Semiconductor","category":"Chips & hardware","exchange":"NYSE","currency":"USD","listingName":"Taiwan Semiconductor Manufacturing Company Ltd.","depositary":false},{"symbol":"TTD","name":"The Trade Desk, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"The Trade Desk, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"TTWO","name":"Take-Two Interactive","category":"Games","exchange":"Nasdaq","currency":"USD","listingName":"Take-Two Interactive Software, Inc. - Common Stock","depositary":false},{"symbol":"TXN","name":"Texas Instruments Incorporated","category":"Chips & hardware","exchange":"Nasdaq","currency":"USD","listingName":"Texas Instruments Incorporated - Common Stock","depositary":false},{"symbol":"U","name":"Unity Software","category":"Games","exchange":"NYSE","currency":"USD","listingName":"Unity Software Inc. Common Stock","depositary":false},{"symbol":"UBER","name":"Uber Technologies, Inc.","category":"Internet & media","exchange":"NYSE","currency":"USD","listingName":"Uber Technologies, Inc. Common Stock","depositary":false},{"symbol":"UNH","name":"UnitedHealth Group Incorporated","category":"Healthcare","exchange":"NYSE","currency":"USD","listingName":"UnitedHealth Group Incorporated Common Stock (DE)","depositary":false},{"symbol":"UNP","name":"Union Pacific Corporation","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Union Pacific Corporation Common Stock","depositary":false},{"symbol":"UPS","name":"United Parcel Service, Inc.","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"United Parcel Service, Inc. Common Stock","depositary":false},{"symbol":"USB","name":"U.S. Bancorp","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"U.S. Bancorp Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"V","name":"Visa Inc.","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Visa Inc.","depositary":false},{"symbol":"VEEV","name":"Veeva Systems Inc. Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Veeva Systems Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"VICI","name":"VICI Properties Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"VICI Properties Inc. Common Stock","depositary":false},{"symbol":"VIK","name":"Viking Holdings Ltd","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Viking Holdings Ltd Ordinary Shares","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"VLO","name":"Valero Energy Corporation","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"Valero Energy Corporation Common Stock","depositary":false},{"symbol":"VRT","name":"Vertiv Holdings, LLC","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Vertiv Holdings, LLC Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"VRTX","name":"Vertex Pharmaceuticals Incorporated","category":"Healthcare","exchange":"Nasdaq","currency":"USD","listingName":"Vertex Pharmaceuticals Incorporated - Common Stock","depositary":false},{"symbol":"VST","name":"Vistra Corp.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Vistra Corp. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"VZ","name":"Verizon Communications Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Verizon Communications Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"W","name":"Wayfair Inc. Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Wayfair Inc. Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"WDAY","name":"Workday, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Workday, Inc. - Class A Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"WEC","name":"WEC Energy Group, Inc.","category":"Utilities","exchange":"NYSE","currency":"USD","listingName":"WEC Energy Group, Inc. Common Stock","depositary":false},{"symbol":"WELL","name":"Welltower Inc.","category":"Property","exchange":"NYSE","currency":"USD","listingName":"Welltower Inc. Common Stock","depositary":false},{"symbol":"WFC","name":"Wells Fargo & Company","category":"Banking & finance","exchange":"NYSE","currency":"USD","listingName":"Wells Fargo & Company Common Stock","depositary":false},{"symbol":"WING","name":"Wingstop Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Wingstop Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"WM","name":"Waste Management, Inc.","category":"Industry & transport","exchange":"NYSE","currency":"USD","listingName":"Waste Management, Inc. Common Stock","depositary":false},{"symbol":"WMT","name":"Walmart Inc.","category":"Shops & travel","exchange":"Nasdaq","currency":"USD","listingName":"Walmart Inc. - Common Stock","depositary":false},{"symbol":"WULF","name":"TeraWulf Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"TeraWulf Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"WYNN","name":"Wynn Resorts, Limited","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Wynn Resorts, Limited - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"},{"symbol":"XEL","name":"Xcel Energy Inc.","category":"Utilities","exchange":"Nasdaq","currency":"USD","listingName":"Xcel Energy Inc. - Common Stock","depositary":false},{"symbol":"XOM","name":"ExxonMobil Holdings Corporation","category":"Energy","exchange":"NYSE","currency":"USD","listingName":"ExxonMobil Holdings Corporation Common Stock","depositary":false},{"symbol":"XPEV","name":"XPeng Inc. American depositary shares, each representing two Class A","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"XPeng Inc. American depositary shares, each representing two Class A ordinary shares","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"YUM","name":"Yum! Brands, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Yum! Brands, Inc.","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ZBH","name":"Zimmer Biomet Holdings, Inc.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Zimmer Biomet Holdings, Inc. Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ZETA","name":"Zeta Global Holdings Corp.","category":"More US listings","exchange":"NYSE","currency":"USD","listingName":"Zeta Global Holdings Corp. Class A Common Stock","depositary":false,"checkedAt":"2026-11-06","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"},{"symbol":"ZS","name":"Zscaler, Inc.","category":"More US listings","exchange":"Nasdaq","currency":"USD","listingName":"Zscaler, Inc. - Common Stock","depositary":false,"checkedAt":"2026-11-15","listingSource":"https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"}]);
const DIRECTORY_BY_SYMBOL = Object.freeze(Object.fromEntries(STOCK_DIRECTORY.map(x=>[x.symbol,x])));
Object.assign(STOCK_NAMES,Object.fromEntries(STOCK_DIRECTORY.map(x=>[x.symbol,x.name])));

const E = {quotes:new Map(), quoteFailures:new Map(), quoteChecks:new Map(), trades:new Map(), subscribed:new Set(), names:{...STOCK_NAMES}, watch:[], view:'overview',selected:'AAPL',range:'1D',chartPoints:[],chartSource:'',chartDomain:null,savedSession:false,chartForecast:null,forecastEnabled:true,forecastNews:new Map(),chartHover:null, ws:null,wsOpen:false, verifiedAt:0, wsRetry:0, wsRetryTimer:null, wsManualClose:false, key:'', configured:false, massiveConfigured:false, news:null, fundamentals:new Map(), candles:new Map(), notes:[], refreshStep:0, busy:false, fetching:false, lastQuoteError:'', lastHistoryStatus:'', lastCandleError:'', tooltip:'', probe:null, probing:false, wsError:'', lastGoodQuoteAt:0,storageError:'',workspaceWarning:'',droppedTicks:0};
// Company aliases identify the listed parent; they are not separate securities.
const STOCK_ALIASES = {TTWO:['Take Two','Take-Two','Take Two Interactive','Rockstar','Rockstar Games','GTA','GTA VI','GTA 6','Grand Theft Auto','Grand Theft Auto VI','Grand Theft Auto 6']};
function localStockMatches(query){
 const normal=s=>String(s||'').toUpperCase().replace(/[^A-Z0-9]/g,'');const q=normal(query);if(!q)return [];
 const rank=s=>normal(s)===q?0:normal(s).startsWith(q)?1:2;
 return Object.entries({...STOCK_NAMES,...E.names}).filter(([symbol,name])=>[symbol,name,...(STOCK_ALIASES[symbol]||[])].some(x=>normal(x).includes(q)))
 .sort(([a],[b])=>rank(a)-rank(b)||a.localeCompare(b))
 .map(([symbol,description])=>({symbol,description,type:symbol==='TTWO'?'Listed parent of Rockstar Games · Nasdaq · USD':DIRECTORY_BY_SYMBOL[symbol]?DIRECTORY_BY_SYMBOL[symbol].category+' · '+DIRECTORY_BY_SYMBOL[symbol].exchange+' · USD':'Known company',displaySymbol:symbol})).slice(0,18);
}
let directoryPage=0,directoryRenderKey='';
function directoryMatches(query='',category='All'){
 const q=String(query).trim().toUpperCase();const aliasSymbols=new Set(q?localStockMatches(q).map(x=>x.symbol):[]);
 return STOCK_DIRECTORY.filter(x=>(category==='All'||x.category===category)&&(!q||aliasSymbols.has(x.symbol)||[x.symbol,x.name,x.listingName,x.category].some(v=>v.toUpperCase().includes(q))));
}
function renderStockDirectory(){
 const grid=$('directory-results');if(!grid)return;
 const query=$('directory-search').value,category=$('directory-category').value||'All',rows=directoryMatches(query,category),size=18;
 directoryPage=Math.max(0,Math.min(directoryPage,Math.max(0,Math.ceil(rows.length/size)-1)));
 const renderKey=JSON.stringify([query,category,directoryPage,E.watch]);if(renderKey===directoryRenderKey)return;directoryRenderKey=renderKey;
 const shown=rows.slice(directoryPage*size,(directoryPage+1)*size);
 $('directory-count').textContent=rows.length+' matching stocks · '+STOCK_DIRECTORY.length+' in the directory';
 grid.innerHTML=shown.length?shown.map(x=>`<article class="directory-stock"><div><strong>${escapeHtml(x.symbol)}</strong><h3>${escapeHtml(x.name)}</h3><p>${escapeHtml(x.category)} · ${escapeHtml(x.exchange)} · USD${x.depositary?' · depositary shares':''}</p></div><button type="button" class="ghost-btn" data-select="${escapeHtml(x.symbol)}">Open chart ↗</button><button type="button" class="link-btn" data-add="${escapeHtml(x.symbol)}" data-name="${escapeHtml(x.name)}">${E.watch.includes(x.symbol)?'Following':'+ Follow'}</button></article>`).join(''):'<p>No matches. Try another name or category, or use the Finnhub search below.</p>';
 $('directory-page').textContent='Page '+(directoryPage+1)+' of '+Math.max(1,Math.ceil(rows.length/size));
 $('directory-prev').disabled=directoryPage===0;$('directory-next').disabled=(directoryPage+1)*size>=rows.length;
}
function setupStockDirectory(){
 const select=$('directory-category');if(!select)return;
 for(const name of [...new Set(STOCK_DIRECTORY.map(x=>x.category))]){const op=document.createElement('option');op.value=name;op.textContent=name;select.appendChild(op);}
 const reset=()=>{directoryPage=0;renderStockDirectory();};select.addEventListener('change',reset);$('directory-search').addEventListener('input',reset);
 $('directory-prev').addEventListener('click',()=>{directoryPage--;renderStockDirectory();});$('directory-next').addEventListener('click',()=>{directoryPage++;renderStockDirectory();});renderStockDirectory();
}

let marketTab='watch',marketRowsKey='',nextQuoteCycleAt=0;
const QUOTE_CYCLE_MS=25000;
function switchMarketsTab(tab,focus=false){
 if(!['watch','explore'].includes(tab))return;marketTab=tab;
 for(const name of ['watch','explore']){const active=name===tab,button=$('market-tab-'+name),panel=$('market-panel-'+name);if(!button||!panel)continue;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;panel.hidden=!active;if(active&&focus)button.focus();}
 if(tab==='explore')renderStockDirectory();else renderMarkets();
}
function setupMarketTabs(){
 document.querySelectorAll('[data-market-tab]').forEach(button=>{button.addEventListener('click',()=>switchMarketsTab(button.dataset.marketTab));button.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tab=e.key==='Home'?'watch':e.key==='End'?'explore':marketTab==='watch'?'explore':'watch';switchMarketsTab(tab,true);});});
 switchMarketsTab('watch');
}
function normaliseWatchlist(stored){return Array.isArray(stored)?[...new Set(stored.map(s=>String(s).toUpperCase()).filter(safeSymbol))].slice(0,60):DEFAULT_STOCKS.slice();}
function nextQuoteCheck(sym,at=nowMs()){
 if(!E.watch.includes(sym))return 'Not on your watchlist';
 if(!E.configured)return 'Add a Finnhub key to check prices';
 if(typeof navigator!=='undefined'&&navigator.onLine===false)return 'Browser offline · waiting to retry';
 if(E.quoteChecks.get(sym)?.busy)return 'Checking this stock now';
 if(E.fetching)return 'Waiting for the current price requests';
 if(!nextQuoteCycleAt)return 'Waiting for the first scheduled check';
 if(nextQuoteCycleAt<=at)return 'Planned check delayed · waiting for the app';
 const length=E.watch.length,start=E.refreshStep%length,index=E.watch.indexOf(sym),offset=(index-start+length)%length;
 const seconds=Math.ceil((nextQuoteCycleAt+Math.floor(offset/6)*QUOTE_CYCLE_MS-at)/1000);
 return 'Next planned check in about '+seconds+'s · provider delays are possible';
}
function freshnessInfo(sym,at=nowMs()){
 const q=quoteFor(sym),check=E.quoteChecks.get(sym);let label=!q?'No price received':q.type==='live'?'Recent confirmed trade':q.stale?'Old price · not live':'Price quote · not a confirmed trade';
 const age=q?Math.max(0,at-q.t):null;
 const recorded=q?'Recorded '+fmtDateTime(q.t)+' · '+(q.t>at?'provider time is ahead of this Mac':age<60000?Math.floor(age/1000)+'s ago':age<3600000?Math.floor(age/60000)+'m ago':age<86400000?Math.floor(age/3600000)+'h ago':Math.floor(age/86400000)+'d ago'):'No recorded price time yet';
 const checked=check?.checkedAt?'Last successful quote check '+elapsed(check.checkedAt)+(check.cached?' · provider returned saved data':''):'No successful quote check this session';
 const warning=check?.error||E.quoteFailures.get(sym)||'';
 return {q,label,recorded,checked,next:nextQuoteCheck(sym,at),warning};
}
function freshnessHTML(sym){const f=freshnessInfo(sym);return `<strong class="freshness-state ${f.q?.stale?'is-old':''}">${escapeHtml(f.label)}</strong><small>${escapeHtml(f.recorded)}</small><small>${escapeHtml(f.checked)}</small><small>${escapeHtml(f.next)}</small>${f.warning?`<small class="freshness-warning">${escapeHtml(f.warning)}</small>`:''}`;}
function refreshWatchFreshness(){
 document.querySelectorAll('[data-watch-symbol]').forEach(row=>{const sym=row.dataset.watchSymbol,f=freshnessInfo(sym),price=row.querySelector('.m-price'),change=row.querySelector('.m-change'),source=row.querySelector('.m-source');if(price)price.textContent=f.q?fmtUnit(sym,f.q.p):'—';if(change){change.textContent=f.q?fmtPct(f.q.change):'—';change.className='m-change '+(f.q?signClass(f.q.change):'neutral');}if(source)source.innerHTML=freshnessHTML(sym);});
 const label=$('research-stock-name'),fresh=$('research-stock-freshness');if(label)label.textContent=E.selected?E.selected+' · '+safeName(E.selected):'Choose a stock';if(fresh){const f=freshnessInfo(E.selected);fresh.textContent=f.label+(f.q?' · '+fmtDateTime(f.q.t):'');}
}
function openStock(sym,heatmapWindow=null){if(!safeSymbol(sym))return;E.heatmapWindow=heatmapWindow;setSelected(sym);renderPickers();refreshWatchFreshness();changeView(document.getElementById('home43-chart')?'home':'overview');setTimeout(()=>{const pane=$('main-chart-panel');if(pane?.scrollIntoView)pane.scrollIntoView({block:'nearest',behavior:'smooth'});},0);}
function openStockResearch(view){if(!['company','intelligence'].includes(view))return;renderPickers();if($('company-select'))$('company-select').value=E.selected;changeView(view);}

const nowMs = () => Date.now();
const safeSymbol = s => /^[A-Z0-9][A-Z0-9.\-:_]{0,23}$/.test(s);
const fmtPrice = (x, digits=2) => Number.isFinite(+x) && +x>0 ? Number(x).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits}) : '—';
const fmtNum = (x, digits=1) => Number.isFinite(+x) ? Number(x).toLocaleString('en-US',{maximumFractionDigits:digits}):'—';
const fmtPct = x => x!==null && x!==undefined && x!=='' && Number.isFinite(+x) ? `${x>=0?'+':''}${(+x).toFixed(2)}%` : '—';
const signClass = x => Number(x)>0?'positive':Number(x)<0?'negative':'neutral';
const fmtUnit = (sym,p) => {const c=DIRECTORY_BY_SYMBOL[sym]?.currency||String(E.fundamentals.get(sym)?.profile?.currency||'').toUpperCase();const val=fmtPrice(p);if(c==='USD'||(!c&&DEFAULT_STOCKS.includes(sym)))return '$'+val;if(c==='GBP')return '£'+val;if(c==='GBX')return val+'p';if(c==='EUR')return '€'+val;return c?val+' '+c:val};
const fmtDate = ms => Number.isFinite(ms) && ms>0?new Date(ms).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false}):'Unavailable';
const fmtDateTime = ms => Number.isFinite(ms) && ms>0?new Date(ms).toLocaleString('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}):'Unavailable';
const elapsed = ms => {if(!ms)return '—';let s=Math.max(0,Math.floor((nowMs()-ms)/1000));return s<60?`${s}s ago`:s<3600?`${Math.floor(s/60)}m ago`:s<86400?`${Math.floor(s/3600)}h ago`:`${Math.floor(s/86400)}d ago`};
const validHttpLink = raw => {try{const u=new URL(raw);return ['https:','http:'].includes(u.protocol)?u.href:''}catch{return ''}};
const savedJSON=(key,fallback)=>{try{const v=JSON.parse(localStorage.getItem(key));return v??fallback}catch{return fallback}};
const BACKUP_KEYS=['md-analyst-drafts-v35','md-reborn-watch','md-reborn-names','md-reborn-notes','md-reborn-reports','md-reborn-portfolio','md-reborn-workstation-v1','md-tape-symbol','md-reborn-v3','md-reborn-journal'];
let backupTimer=0,backupReady=false,backupSaving=false,backupAgain=false;
function recoveryDrafts(allowDamaged=false){try{const raw=localStorage.getItem('md-analyst-drafts-v35'),d=raw?JSON.parse(raw):{version:1,records:[]};if(!d||!Array.isArray(d.records)||d.records.length>10)throw Error();return d;}catch{if(allowDamaged)return {version:1,records:[]};throw Error('Draft recovery data needs checking. Download its raw copy in Intelligence. Existing backup data was not replaced.');}}
function snapshotWorkspace(allowDamagedDrafts=false){return {analystDrafts:recoveryDrafts(allowDamagedDrafts),watch:savedJSON('md-reborn-watch',DEFAULT_STOCKS),names:savedJSON('md-reborn-names',{}),notes:savedJSON('md-reborn-notes',[]),journal:savedJSON('md-reborn-journal',[]),reports:savedJSON('md-reborn-reports',[]),portfolio:savedJSON('md-reborn-portfolio',{capital:10000,trades:[]}),preferences:savedJSON('md-reborn-workstation-v1',{}),design:savedJSON('md-reborn-design-v28',{}),v3:savedJSON('md-reborn-v3',{}),tapeSymbol:savedJSON('md-tape-symbol','AAPL')}}
async function sendWorkspaceBackup(){
  if(!backupReady)return;
  if(backupSaving){backupAgain=true;return}
  backupSaving=true;
  try{
    const data=await post('/api/workspace',{snapshot:snapshotWorkspace()});
    localStorage.setItem('md-workspace-server-synced',String(data.updated_at));
    const info=$('workspace-backup-status');if(info)info.textContent='✓ Watchlist, notes, reports, paper portfolio and preferences backed up to this Mac · '+fmtDateTime(data.updated_at)+(E.workspaceWarning?' · Recovery notice: '+E.workspaceWarning:'');
  }catch(err){
    const info=$('workspace-backup-status');if(info)info.textContent='Backup failed: '+err.message+' · Browser copies remain available';
    console.warn('Workspace backup failed:',err.message);
  }finally{backupSaving=false;if(backupAgain){backupAgain=false;queueWorkspaceBackup()}}
}
function queueWorkspaceBackup(){if(!backupReady)return;clearTimeout(backupTimer);backupTimer=setTimeout(sendWorkspaceBackup,200)}
const saveJSON=(key,val)=>{try{localStorage.setItem(key,JSON.stringify(val));if(BACKUP_KEYS.includes(key))queueWorkspaceBackup()}catch{toast('Local browser storage unavailable.')}};
function commitBrowserRecords(records){
  const entries=Object.entries(records).filter(([,v])=>v!==undefined&&v!==null).map(([k,v])=>[k,JSON.stringify(v)]);
  const previous=new Map(entries.map(([key])=>[key,localStorage.getItem(key)]));
  try{for(const [key,value] of entries)localStorage.setItem(key,value)}
  catch(error){
    // Release only the attempted keys before restoring them: a quota failure
    // must not leave half an imported workspace accepted as a successful save.
    try{for(const [key] of entries)localStorage.removeItem(key);for(const [key,value] of previous)if(value!==null)localStorage.setItem(key,value)}
    catch{throw Error('Browser storage failed during recovery. Keep this page open and export your current research before retrying.');}
    throw Error('Browser storage is full or unavailable. The previous records were restored; no import was accepted.');
  }
}
async function restoreWorkspace(){
  try{
    const {snapshot,updated_at:remoteStamp,warning:recoveryWarning}=await api('/api/workspace');
    E.workspaceWarning=recoveryWarning||'';
    if(recoveryWarning){const info=$('workspace-backup-status');if(info)info.textContent=recoveryWarning;}
    if(snapshot){
      const lastSynced=Number(localStorage.getItem('md-workspace-server-synced')||0);
      const current=snapshotWorkspace(true);
      const localWatch=localStorage.getItem('md-reborn-watch')!==null;
      const useServer=remoteStamp>lastSynced && lastSynced>0;
      const merged={...snapshot};
      if(!useServer && localWatch){
        // Migrate earlier Market Desk versions, keeping local notes and watched stocks.
        merged.watch=normaliseWatchlist(current.watch); // Keep local removals, including an intentionally empty list.
        merged.names={...(snapshot.names||{}),...(current.names||{})};
        const notes=[...(Array.isArray(current.notes)?current.notes:[]),...(snapshot.notes||[])];
        const ids=new Set();merged.notes=notes.filter(n=>{const id=JSON.stringify([n.title,n.date,n.thesis]);if(ids.has(id))return false;ids.add(id);return true}).slice(0,250);
        merged.journal=(typeof Journal49!=='undefined'?Journal49.merge(current.journal,snapshot.journal):snapshot.journal||current.journal||[]);
        merged.reports=mergeReportArchives(current.reports,snapshot.reports);
        merged.portfolio=localStorage.getItem('md-reborn-portfolio')!==null?current.portfolio:snapshot.portfolio;
        merged.v3=localStorage.getItem('md-reborn-v3')!==null?current.v3:snapshot.v3;
        merged.design=localStorage.getItem('md-reborn-design-v28')!==null?current.design:snapshot.design;
        merged.preferences=localStorage.getItem('md-reborn-workstation-v1')!==null?current.preferences:snapshot.preferences;
        merged.tapeSymbol=localStorage.getItem('md-tape-symbol')!==null?current.tapeSymbol:snapshot.tapeSymbol;
      }
      merged.reports=mergeReportArchives(current.reports,snapshot.reports);
      merged.portfolio=localStorage.getItem('md-reborn-portfolio')!==null?current.portfolio:snapshot.portfolio;
      merged.analystDrafts=localStorage.getItem('md-analyst-drafts-v35')!==null?current.analystDrafts:snapshot.analystDrafts;
      merged.journal=(typeof Journal49!=='undefined'?Journal49.merge(current.journal,snapshot.journal):snapshot.journal||current.journal||[]);
      const mapping={'md-analyst-drafts-v35':merged.analystDrafts,'md-reborn-watch':merged.watch,'md-reborn-names':merged.names,'md-reborn-notes':merged.notes,'md-reborn-journal':merged.journal,'md-reborn-reports':merged.reports,'md-reborn-portfolio':merged.portfolio,'md-reborn-workstation-v1':merged.preferences,'md-reborn-design-v28':merged.design,'md-reborn-v3':merged.v3,'md-tape-symbol':merged.tapeSymbol};
      if(localStorage.getItem('md-analyst-drafts-v35')!==null)delete mapping['md-analyst-drafts-v35'];
      commitBrowserRecords(mapping);
      window.dispatchEvent(new Event('marketdesk:workspace-restored'));
    }
    backupReady=true;
    queueWorkspaceBackup();
  }catch(e){
    console.warn('Backup not accessible; browser data remains available:',e.message);
    const info=$('workspace-backup-status');if(info)info.textContent='Backup unavailable; existing browser data remains accessible. '+e.message;
    backupReady=true;
  }
}

async function api(path, options={}){const resp=await fetch(path,{cache:'no-store',...options});let data;try{data=await resp.json()}catch{throw new Error('Invalid response from the local server.')}if(!resp.ok)throw new Error(data.error||'Request failed (HTTP '+resp.status+').');return data}
async function post(path, data){return api(path,{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(data)})}
let toastTimer;function toast(msg){const el=$('toast');el.textContent=msg;el.classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add('hidden'),5000)}
function alertBanner(msg){const el=$('global-alert');if(!msg){el.classList.add('hidden');return;}el.textContent=msg;el.classList.remove('hidden')}
function safeName(sym){return E.names[sym]||sym}
function quoteFor(sym){
  const t=E.trades.get(sym),q=E.quotes.get(sym),time=nowMs();
  if(E.wsOpen&&t&&t.v>0&&time-t.receivedAt<180000&&time-t.t<300000&&t.t<=time+60000&&(!q||t.t>=(q.quote?.t||0)*1000))
    return {p:t.p,t:t.t,source:'VERIFIED FINNHUB TRADE',type:'live',receivedAt:t.receivedAt,change:q?.quote?.pc?100*(t.p-q.quote.pc)/q.quote.pc:null};
  if(q?.quote){
    const providerTime=q.quote.t*1000;
    const stale=time-providerTime>15*60000;
    return {p:q.quote.c,t:providerTime,source:stale?'STALE FINNHUB QUOTE':'FINNHUB QUOTE',type:stale?'stale':'quote',change:q.quote.dp,receivedAt:q.receivedAt,stale};
  }
  return null;
}
function currentMode(){if(E.wsOpen&&E.verifiedAt && nowMs()-E.verifiedAt<180000)return 'live';if(E.lastGoodQuoteAt && nowMs()-E.lastGoodQuoteAt<180000)return 'quotes';if(E.wsOpen)return 'waiting';return E.configured?'error':'offline'}
function syncConnectionUI(){
  const mode=currentMode();
  const captions={live:'VERIFIED TRADE FEED',quotes:'QUOTE SNAPSHOTS',waiting:'STREAM OPEN · NO CONFIRMED TRADE',error:'QUOTES UNAVAILABLE',offline:'FEED OFFLINE'};
  const colors={live:'green',quotes:'amber',waiting:'amber',error:'red',offline:'red'};
  for(const id of ['connection-dot','top-dot'])$(id).className='status-dot '+colors[mode];
  $('top-status').textContent=captions[mode];
  $('connection-label').textContent=mode==='live'?'Verified trade data':mode==='quotes'?'Finnhub quotes received':mode==='waiting'?'Waiting for genuine trades':mode==='error'?'Quote connection not verified':'No data connection';
  $('connection-sub').textContent=mode==='live'?'Provider WebSocket trade':mode==='quotes'?'Snapshots, not live ticks':mode==='waiting'?'Socket transport only':mode==='error'?'Run the Connection Check':'Finnhub market data';
  $('integrity-stream').textContent=mode==='live'?'Verified trade · '+elapsed(E.verifiedAt):'No recent verified tick';
  $('diag-ws').textContent=E.wsError|| (E.wsOpen?'Connected · awaiting verified tick':'Not connected');
  $('diag-trades').textContent=mode==='live'?'Latest '+elapsed(E.verifiedAt):E.verifiedAt?'Last tick '+elapsed(E.verifiedAt):'None confirmed';
  $('diag-rest').textContent=E.probe?(E.probe.ok?'Fresh test passed · '+fmtDateTime(E.probe.checked_at):'Test failed · '+E.probe.kind.replaceAll('_',' ')):E.lastQuoteError?'Quote request failed':E.lastGoodQuoteAt?'Quote snapshots received':'Not tested';
  $('key-state').textContent=E.configured?'SAVED LOCALLY':'NOT CONFIGURED';
  $('massive-key-state').textContent=E.massiveConfigured?'SAVED PRIVATELY':'NOT CONFIGURED';
  $('diag-server').textContent='Running locally';
}

function changeView(view){if(typeof AppDesign!=='undefined'){return AppDesign.page(view,()=>commitView(view));}return commitView(view)}
function commitView(view){if(!$("view-"+view))return;const previousView=E.view;E.view=view;if(typeof Crypto38!=='undefined'&&previousView!==view){if(previousView==='crypto')Crypto38.close();if(view==='crypto')Crypto38.open();}if(previousView!==view&&(['overview','tape'].includes(previousView)||['overview','tape'].includes(view)))resubscribe();document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active',el.id==='view-'+view));document.querySelectorAll('.nav-btn').forEach(el=>el.classList.toggle('active',el.dataset.view===view));$('breadcrumb-current').textContent=({home:'Home',calendar:'Company calendar',sources:'Sources & health',heatmap:'Market Heatmap',learning:'Learning & offline',crypto:'Crypto',screener:'Stock Screener',intelligence:'Market Desk Intelligence',alerts:'Price Alerts',overview:'Overview',markets:'Stock Browser',company:'Company Overview',forecast:'Price Forecasts',news:'Market News',research:'Research projects',comparison:'Compare Companies',reports:'Research Reports',macro:'Economy Overview',accuracy:'Forecast Results',settings:'Settings & Checks',tape:'Live Tape',indicators:'Chart Indicators',valuation:'Company Valuation',portfolio:'Practice Portfolio'})[view];$('sidebar').classList.remove('open');if(view==='learning'&&typeof Workbench40!=='undefined')Workbench40.open();if(view==='heatmap')Heatmap.open();if(view==='screener')Screener.open();if(view==='alerts')PriceAlerts.open();if(view==='intelligence')MDI.open();if(view==='markets')renderMarkets();if(view==='comparison'&&typeof compareOnView==='function')compareOnView();if(['indicators','valuation','portfolio'].includes(view)&&typeof v19OnView==='function')v19OnView(view);if(view==='reports'&&typeof reportsOnView==='function')reportsOnView();if(view==='macro'&&typeof macroOnView==='function')macroOnView();if(view==='accuracy'&&typeof accuracyOnView==='function')accuracyOnView();if(view==='tape' && typeof tapeOnView==='function')tapeOnView();if(view==='company'){if(typeof FinancialHealth!=='undefined')FinancialHealth.open();else loadCompany()}if(view==='news')loadNews();if(view==='research')renderNotes();if(view==='settings'){runDiagnostics();runLocalAudit()}if(view==='overview'){if(typeof Desk!=='undefined')Desk.open();setTimeout(drawChart,80);}if(typeof V3!=='undefined')V3.open(view);if(typeof Projects32!=='undefined')Projects32.open(view);if(typeof Briefing33!=='undefined')Briefing33.open(view);if(typeof Analyst34!=='undefined')Analyst34.open(view);window.scrollTo(0,0)}
function toggleExpandedChart(force){
  const pane=$('main-chart-panel');
  const expanded=typeof force==='boolean'?force:!pane.classList.contains('is-expanded');
  if(expanded&&typeof AppDesign!=='undefined')AppDesign.flush();
  pane.classList.toggle('is-expanded',expanded);
  $('chart-expand').textContent=expanded?'✕ Close full-screen':'⤢ Expand chart';
  $('chart-expand').setAttribute('aria-expanded',String(expanded));
  document.body.classList.toggle('chart-modal-open',expanded);
  setTimeout(drawChart,80);
}
function followInvestigation(previous,sym){
  const same=element=>element&&(!element.value||String(element.value).toUpperCase()===String(previous||'').toUpperCase());
  const scenario=$('scenario53-symbol');if(same(scenario))scenario.value=sym;
  const pack=$('pack59-symbol');if(same(pack))pack.value=sym;
  const compare=$('compare-a');if(same(compare))compare.value=sym;
  const dates=E.investigation;
  if(dates&&dates.symbol===sym){
    const start=$('compare52-start'),end=$('compare52-end');
    if(start&&!start.value)start.value=dates.start||'';
    if(end&&!end.value)end.value=dates.end||'';
  }
}
function setSelected(sym){
  if(!safeSymbol(sym))return;
  resetSessionReplay();
  const previous=E.selected;
  const changed=E.selected!==sym;
  if(changed&&window.Practice67?.active)Practice67.onSymbol(sym);
  else if(changed&&window.Replay43?.active)Chart43.backToLive();
  E.selected=sym;
  followInvestigation(previous,sym);
  E.selectionSeq=(E.selectionSeq||0)+1;
  if(changed){E.forecastFocus=false;E.chartPoints=[];E.chartForecast=null;E.chartSource='Loading recorded prices';E.chartHover=null;drawChart()}
  renderPickers();if($('company-select'))$('company-select').value=sym;
  if($('forecast-select'))$('forecast-select').value=sym;
  if(changed&&E.view==='overview')resubscribe();
  if(changed&&E.view==='news')loadNews(false);
  if(changed&&E.view==='company'){if(window.Events42?.open)Events42.open();if(window.FinancialHealth?.load)FinancialHealth.load();}
  if(changed){forecastRunId++;const pane=$('forecast-content');if(pane)pane.innerHTML='<div class="empty-state"><h3>Research follows '+escapeHtml(sym)+'</h3><p>The previous forecast was cleared so a late result cannot replace this company.</p></div>';window.Move44?.clear()}
  if(typeof Desk!=='undefined')Desk.selected();renderOverview();loadChart();window.Look43?.refresh();
}
function companyChoices(){return [...new Set([...STOCK_DIRECTORY.map(x=>x.symbol),...E.watch,...(E.selected?[E.selected]:[])])]}
function browseSymbols(){return [...new Set([...(E.selected?[E.selected]:[]),...E.watch])].slice(0,60)}
function renderPickers(){if(typeof researchUpdatePickers==='function')researchUpdatePickers();for(const el of [$('company-select'),$('forecast-select')]){let current=el.value;el.replaceChildren();for(const s of companyChoices()){let op=document.createElement('option');op.value=s;op.textContent=`${s}  /  ${safeName(s)}`;el.appendChild(op)}el.value=companyChoices().includes(current)?current:(E.selected||E.watch[0]||'')}}
function addStock(symbol,name){const sym=String(symbol||'').trim().toUpperCase();if(!safeSymbol(sym)){toast('Invalid ticker symbol.');return}if(E.watch.includes(sym)){openStock(sym);return}if(E.watch.length>=60){toast('Watchlist limit is 60 stocks. Remove a symbol first.');return}E.watch.push(sym);if(name)E.names[sym]=name;saveJSON('md-reborn-watch',E.watch);saveJSON('md-reborn-names',E.names);renderAll();loadQuotes([sym]);resubscribe();toast(sym+' added to watchlist')}
function removeStock(sym){
  const wasSelected=E.selected===sym;
  E.watch=E.watch.filter(s=>s!==sym);
  saveJSON('md-reborn-watch',E.watch);
  E.quoteChecks.delete(sym);E.quoteFailures.delete(sym);
  if(wasSelected){E.selected='';if(E.watch.length)setSelected(E.watch[0]);else{E.chartPoints=[];E.chartForecast=null;E.chartSource='No stock selected';drawChart()}}
  renderAll();resubscribe();toast(sym+' removed');
}
function heroHTML(sym){const q=quoteFor(sym);return `<div class="hero-card" data-select="${escapeHtml(sym)}" role="button" tabindex="0"><div class="hero-top"><span class="hero-symbol">${escapeHtml(sym)}</span><span class="hero-name">${escapeHtml(safeName(sym).slice(0,23))}</span></div><div class="hero-price">${q?fmtUnit(sym,q.p):'—'}</div><div class="hero-bottom"><span class="hero-change ${q?signClass(q.change):'neutral'}">${q?fmtPct(q.change):'Waiting for a price'}</span><span class="hero-age">${q?(q.stale?'STALE · ':'')+elapsed(q.t):'NO DATA'}</span></div></div>`}
function renderOverview(){if(typeof Desk!=='undefined')Desk.memory();let featured=E.watch.slice(0,4);$('overview-hero').innerHTML=featured.map(heroHTML).join('');$('overview-watchlist').innerHTML=E.watch.slice(0,7).map(sym=>{let q=quoteFor(sym);return `<div class="watch-row" data-select="${escapeHtml(sym)}" role="button" tabindex="0"><div class="watch-company"><span class="symbol-avatar">${escapeHtml(sym.slice(0,2))}</span><div style="min-width:0"><div class="watch-name">${escapeHtml(safeName(sym))}</div><div class="watch-ticker">${escapeHtml(sym)}</div></div></div><span class="watch-value">${q?fmtUnit(sym,q.p):'—'}</span><span class="watch-change ${q?signClass(q.change):'neutral'}">${q?fmtPct(q.change):'—'}</span></div>`}).join('');const selected=quoteFor(E.selected);$('overview-chart-name').innerHTML=E.selected?`${escapeHtml(safeName(E.selected))} <span>${escapeHtml(E.selected)}</span>`:'Choose a stock to see its chart';$('overview-chart-price').textContent=selected?fmtUnit(E.selected,selected.p):'—';$('overview-chart-source').textContent=E.chartPoints.length>1?E.chartSource:(selected?selected.source:'AWAITING DATA');$('integrity-history').textContent=E.lastHistoryStatus||'Not checked yet'}
function renderMarkets(){
 $('watch-count').textContent=E.watch.length;const tab=$('market-tab-watch');if(tab)tab.textContent='My watchlist ('+E.watch.length+')';
 const key=JSON.stringify(E.watch.map(sym=>[sym,safeName(sym)]));
 if(key!==marketRowsKey){marketRowsKey=key;$('markets-table').innerHTML=E.watch.length?E.watch.map(sym=>{const q=quoteFor(sym);return `<div class="market-row data-row" data-watch-symbol="${escapeHtml(sym)}"><div class="market-company" data-select="${escapeHtml(sym)}" role="button" tabindex="0" aria-label="Open ${escapeHtml(safeName(sym))} chart and research"><span class="symbol-avatar">${escapeHtml(sym.slice(0,2))}</span><div><div class="m-company">${escapeHtml(safeName(sym))}</div><div class="watch-ticker">${escapeHtml(sym)} · Open chart ↗</div></div></div><div class="m-price">${q?fmtUnit(sym,q.p):'—'}</div><div class="m-change ${q?signClass(q.change):'neutral'}">${q?fmtPct(q.change):'—'}</div><div class="m-source">${freshnessHTML(sym)}</div><button class="remove-btn" data-remove="${escapeHtml(sym)}" aria-label="Remove ${escapeHtml(sym)}">×</button></div>`;}).join(''):'<div class="watch-empty"><h3>Your watchlist is empty</h3><p>Choose Explore stocks to find companies and add the ones you want to follow. Your empty list will stay empty when you reopen the app.</p><button class="primary-btn" data-market-tab-link="explore">Explore stocks ↗</button></div>';}
 $('market-update-status').textContent=E.lastQuoteError?'Provider: '+E.lastQuoteError.slice(0,160):'Background quotes rotate across the watchlist · larger lists take longer';
 refreshWatchFreshness();if(marketTab==='explore')renderStockDirectory();
}

let tickerSymbols='';
function updateTicker(){
  const quotes=E.watch.slice(0,12).map(s=>({s,q:quoteFor(s)})).filter(x=>x.q);
  const track=$('ticker-track');
  if(!quotes.length){
    tickerSymbols='';track.classList.remove('moving');
    track.innerHTML='<span class="ticker-intro">MARKET PULSE <span>●</span></span><span class="ticker-placeholder">Finnhub prices appear here when a genuine response arrives. No sample data.</span>';
    return;
  }
  const key=quotes.map(x=>x.s).join('|');
  if(key!==tickerSymbols){
    tickerSymbols=key;
    const html=quotes.map(({s})=>`<span class="ticker-item" data-pulse="${escapeHtml(s)}"><b>${escapeHtml(s)}</b><span class="tick-price">—</span><strong>—</strong><span class="ticker-label">QUOTE</span></span>`).join('');
    const block='<span class="ticker-intro">MARKET PULSE <span>●</span></span>'+html;
    track.innerHTML=block+block;
    track.classList.add('moving');
  }
  // Update text nodes in place; never reset the animation on every trade tick.
  track.querySelectorAll('[data-pulse]').forEach(row=>{
    const sym=row.dataset.pulse,q=quoteFor(sym);if(!q)return;
    row.querySelector('.tick-price').textContent=fmtUnit(sym,q.p);
    const change=row.querySelector('strong');change.textContent=fmtPct(q.change);change.className=signClass(q.change);
    row.querySelector('.ticker-label').textContent=q.type==='live'?'TRADE':q.type==='stale'?'STALE':'QUOTE';
  });
}

function renderAll(){renderOverview();renderMarkets();renderPickers();updateTicker();syncConnectionUI();if(typeof tapeOnMarketData==='function')tapeOnMarketData()}
async function loadQuotes(symbols){
 if(!E.configured||!symbols?.length||E.fetching)return;
 symbols=[...new Set(symbols.filter(sym=>safeSymbol(sym)&&E.watch.includes(sym)))];if(!symbols.length)return;
 E.fetching=true;const errors=[];
 try{
  for(let i=0;i<symbols.length;i+=6){
   const chunk=symbols.slice(i,i+6);for(const sym of chunk)E.quoteChecks.set(sym,{...E.quoteChecks.get(sym),busy:true,attemptedAt:nowMs()});
   try{
    const data=await api('/api/quotes?symbols='+encodeURIComponent(chunk.join(','))),items=new Map((data.items||[]).map(item=>[item.symbol,item]));
    for(const sym of chunk){
     if(!E.watch.includes(sym)){E.quoteChecks.delete(sym);continue;}
     const item=items.get(sym),q=item?.quote,valid=q&&Number.isFinite(q.c)&&q.c>0&&q.c<=1e9&&Number.isInteger(q.t)&&q.t>=946684800&&q.t*1000<=nowMs()+60000;
     if(valid){
      const older=(E.quotes.get(sym)?.quote?.t||0)>q.t;
      if(!older)E.quotes.set(sym,{...item,receivedAt:nowMs()});
      E.quoteChecks.set(sym,{busy:false,attemptedAt:E.quoteChecks.get(sym)?.attemptedAt,checkedAt:nowMs(),cached:Boolean(item.cached),error:older?'Provider returned an older quote; keeping the later recorded price.':''});
      E.quoteFailures.delete(sym);E.lastGoodQuoteAt=nowMs();
     }else{const message=item?.error||'No valid price was returned for this stock.';E.quoteFailures.set(sym,message);E.quoteChecks.set(sym,{...E.quoteChecks.get(sym),busy:false,error:message});errors.push(sym+': '+message);}
    }
   }catch(e){for(const sym of chunk){if(!E.watch.includes(sym)){E.quoteChecks.delete(sym);continue;}E.quoteFailures.set(sym,e.message);E.quoteChecks.set(sym,{...E.quoteChecks.get(sym),busy:false,error:e.message});}errors.push(e.message);break;}
   if(errors.some(x=>/rate limit|budget|cooldown/i.test(x)))break;
  }
  E.lastQuoteError=errors[0]||'';alertBanner(E.lastQuoteError&&E.quotes.size===0?E.lastQuoteError:'');
 }finally{E.fetching=false;renderAll();if(['1H','1D'].includes(E.range)||E.chartPoints.length>0)loadChart(false);}
}
async function autoQuoteCycle(){
 if(!E.configured||E.fetching||!E.watch.length)return;
 if(E.backgroundCollector){
   E.fetching=true;
   try{
     const symbols=[...new Set([...E.watch,...desiredSubscriptions()])].slice(0,60);
     const data=await api('/api/saved-quotes?symbols='+encodeURIComponent(symbols.join(',')));
     for(const item of data.items||[]){
       if(!E.watch.includes(item.symbol)&&E.selected!==item.symbol)continue;
       const existing=E.quotes.get(item.symbol);
       if(!existing||existing.quote.t<=item.quote.t)E.quotes.set(item.symbol,item);
     }
     renderAll();if(E.view==='overview')loadChart(false);
   }catch{/* Keep saved quotes and their original timestamps. */}
   finally{E.fetching=false;}
   return;
 }
 const visible=E.watch.slice(),start=E.refreshStep%visible.length,batch=[];
 for(let i=0;i<Math.min(6,visible.length);i++)batch.push(visible[(start+i)%visible.length]);
 E.refreshStep=(start+batch.length)%visible.length;await loadQuotes(batch);
}

async function setupTokenStatus(){try{if(location.port&&location.port!=='8765')alertBanner('Market Desk is on a different local port ('+location.port+'). If earlier notes appear missing, close older Market Desk Terminal windows and relaunch on port 8765 before importing/migrating.');const status=await api('/api/status');E.configured=Boolean(status.configured);E.massiveConfigured=Boolean(status.massive_configured);if(E.massiveConfigured&&E.forecastEnabled&&['1H','1D'].includes(E.range)){E.range='1Y';document.querySelectorAll('#overview-ranges button').forEach(b=>b.classList.toggle('active',b.dataset.range==='1Y'));}$('diag-budget').textContent=status.api_used_last_60s+' / '+status.api_budget;E.backgroundCollector=Boolean(status.backgroundCollector);syncConnectionUI();if(E.configured){connectWS();await autoQuoteCycle();loadNews();loadChart();}else if(E.massiveConfigured){loadChart();toast('Massive history is ready; Finnhub live quotes are not connected.');}else{alertBanner('Welcome to Market Desk Reborn. Use All tools → Settings to connect market prices. Local research, SEC accounts and practice tools can be used separately.')}}catch(e){alertBanner('Local server error: '+e.message)}}
let tradeDisplayTimer=null, tradeChartTimer=null;
function appendRecordedTrade(){
  if(!['1H','1D'].includes(E.range))return;
  const trade=E.trades.get(E.selected);
  if(!trade||!Number.isFinite(trade.t)||!Number.isFinite(trade.p))return;
  if(E.chartPoints.some(point=>point.t===trade.t))return;
  E.chartPoints.push({t:trade.t,p:trade.p,source:'finnhub_websocket'});
  E.chartPoints.sort((a,b)=>a.t-b.t);
  drawChart();
}
function scheduleTradeRefresh(updateSelected){
  // Preserve smooth interaction even when the exchange emits many trades per second.
  if(!tradeDisplayTimer) tradeDisplayTimer=setTimeout(()=>{tradeDisplayTimer=null;renderAll()},180);
  // A daily chart is closes, not trades. Reloading it here waited on the forecast and hid the line.
  if(updateSelected&&E.view==='overview'&&['1H','1D'].includes(E.range)&&!tradeChartTimer) tradeChartTimer=setTimeout(()=>{
    tradeChartTimer=null;appendRecordedTrade();
  },950);
}
let streamPoll=0,streamGeneration=0;
function stopWS(){
  streamGeneration++;
  clearTimeout(streamPoll);
  streamPoll=0;
  E.wsOpen=false;E.wsError='';E.subscribed.clear();
}
function acceptCollectorPacket(packet){
  E.wsOpen=packet.status?.stream==='Connected';
  E.wsError=E.wsOpen?'':packet.status?.stream||'Waiting for collector';
  E.subscribed=new Set(packet.symbols||[]);
  const received=[];
  const now=nowMs();
  for(const row of packet.events||[]){
    if(!E.subscribed.has(row.s)||!Number.isFinite(row.p)||row.p<=0||row.p>1e9||
       !Number.isFinite(row.v)||row.v<=0||row.v>1e12||!Number.isInteger(row.t)||
       !Number.isInteger(row.receivedAt)||row.receivedAt>now+5000||
       row.t<now-300000||row.t>now+60000)continue;
    if(!E.trades.has(row.s)||E.trades.get(row.s).t<=row.t)E.trades.set(row.s,row);
    E.verifiedAt=Math.max(E.verifiedAt||0,row.receivedAt);
    received.push(row);
  }
  if(received.length){
    scheduleTradeRefresh(received.some(row=>row.s===E.selected));
    if(typeof tapeOnTrades==='function')tapeOnTrades(received);
  }
  const recovered=E.collectorDown;
  E.collectorDown=false;
  if(packet.gap||recovered){
    const feed=$('look43-feed');
    if(feed)feed.textContent=packet.gap?'Collector found a gap. Reading saved prices.':'Collector reconnected. Reading saved prices.';
    if(['1H','1D'].includes(E.range))loadChart(false);
    if(E.view==='tape'&&typeof tapeReload==='function')tapeReload();
  }
  syncConnectionUI();
}
function connectWS(){
  stopWS();
  if(!E.configured)return;
  const generation=streamGeneration;
  let cursor=0,epoch='';
  async function poll(){
    if(generation!==streamGeneration)return;
    try{
      const priority=E.view==='overview'?E.selected:E.view==='tape'&&typeof tapeSelectedSymbol==='function'?tapeSelectedSymbol():null;
      const packet=await post('/api/collector-pulse',{priority,cursor,epoch});
      if(generation!==streamGeneration)return;
      cursor=packet.cursor||0;epoch=packet.epoch||'';
      acceptCollectorPacket(packet);
      const busy=E.view==='tape'||(packet.events&&packet.events.length);
      streamPoll=setTimeout(poll,document.hidden?8000:busy?1000:3000);
      return;
    }catch{
      if(generation!==streamGeneration)return;
      E.collectorDown=true;E.wsOpen=false;E.wsError='Waiting for local collector';E.subscribed.clear();syncConnectionUI();
    }
    streamPoll=setTimeout(poll,document.hidden?8000:3000);
  }
  poll();
}
function desiredSubscriptions(){
  const priorities=[];
  if(E.view==='overview'&&safeSymbol(E.selected))priorities.push(E.selected);
  const tapeSymbol=typeof tapeSelectedSymbol==='function'?tapeSelectedSymbol():null;
  if(tapeSymbol&&(E.watch.includes(tapeSymbol)||(E.view==='tape'&&DIRECTORY_BY_SYMBOL[tapeSymbol])))priorities.push(tapeSymbol);
  return new Set([...new Set([...priorities,...E.watch])].slice(0,30));
}
function resubscribe(){
  if(E.configured&&!streamPoll)connectWS();
}
async function runDiagnostics(){
  if(E.probing)return;
  E.probing=true;
  const btn=$('diagnostic-refresh');btn.disabled=true;btn.textContent='Checking Finnhub…';
  $('diag-probe').textContent='Testing a fresh AAPL quote…';
  try{
    const probe=await api('/api/diagnose'); E.probe=probe;
    const good=probe.ok;
    $('diag-probe').textContent=good?'✓ Valid quote returned ('+probe.latency_ms+'ms)':'✕ '+probe.kind.replaceAll('_',' ');
    $('diag-probe').className=good?'diag-good':'diag-bad';
    $('diag-tls').textContent=probe.tls_trust||'Unknown';
    $('diag-message').textContent=probe.message+(good&&probe.quote_time_ms?' Provider time: '+fmtDateTime(probe.quote_time_ms)+'.':'');
    $('diag-message').className=good?'diag-result good':'diag-result issue';
    if(good)E.lastGoodQuoteAt=nowMs();
    const status=await api('/api/status');
    $('diag-budget').textContent=status.api_used_last_60s+' / '+status.api_budget;
    $('diag-storage').textContent=E.storageError||('Recording on · '+E.droppedTicks+' dropped events');
    syncConnectionUI();
  }catch(e){
    $('diag-probe').textContent='Local diagnostic failed';
    $('diag-message').textContent=e.message;
    $('diag-message').className='diag-result issue';
  }finally{E.probing=false;btn.disabled=false;btn.textContent='Test connection ↻'}
}

function exportWorkspace(){
 try{
  const data=JSON.stringify({format:'MarketDesk-Research-Backup',version:1,exportedAt:new Date().toISOString(),snapshot:snapshotWorkspace()},null,2);
  const blob=new Blob([data],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='MarketDesk-Research-Backup-'+new Date().toISOString().slice(0,10)+'.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1500);
  toast('Research backup exported. Your private provider keys are not included.');
 }catch(e){toast('Backup export failed: '+e.message)}
}
async function importWorkspace(file){
  if(!file)return;
  if(file.size>2500000){toast('Backup file is too large; please use an exported Market Desk research backup.');return}
  try{
    const payload=JSON.parse(await file.text());
    if(payload?.format!=='MarketDesk-Research-Backup'||payload.version!==1||!payload.snapshot)throw new Error('Not a recognised Market Desk research backup.');
    const raw=payload.snapshot;
    if(!Array.isArray(raw.watch)||!Array.isArray(raw.notes))throw new Error('Incomplete backup file.');
    const watch=[...new Set(raw.watch.map(v=>String(v).toUpperCase()).filter(safeSymbol))].slice(0,60);
    const notes=raw.notes.slice(0,250).filter(x=>x&&typeof x==='object').map(n=>Object.fromEntries(
      ['title','thesis','risk','evidence','date'].map(k=>[k,String(n[k]??'').slice(0,k==='title'?180:k==='date'?90:8000)])));
    const names={};
    if(raw.names&&typeof raw.names==='object'&&!Array.isArray(raw.names))for(const [k,v] of Object.entries(raw.names).slice(0,100)){
      if(safeSymbol(k)&&typeof v==='string')names[k]=v.slice(0,110);
    }
    if(raw.watch.length&&!watch.length)throw new Error('This backup has no valid watchlist symbols.');
    // Validate optional new paper-trading data BEFORE changing any existing workspace fields.
    let cleanPaper=null;
    if(raw.portfolio!==undefined){
      const paper=raw.portfolio;
      if(!paper||!Array.isArray(paper.trades)||paper.trades.length>250)throw new Error('Invalid paper portfolio in this backup.');
      try{MD19Models.portfolio(paper.capital,paper.trades)}catch(err){throw new Error('Invalid paper portfolio: '+err.message)}
      cleanPaper={capital:Number(paper.capital),trades:paper.trades.slice(0,250).map(t=>({symbol:String(t.symbol).toUpperCase(),side:t.side,qty:Number(t.qty),price:Number(t.price),date:String(t.date||'').slice(0,40)}))};
    }
    let cleanDrafts=null;if(raw.analystDrafts!==undefined)cleanDrafts=await post('/api/v3/drafts-validate',{drafts:raw.analystDrafts});
    let cleanV3=null;if(raw.v3!==undefined){const checked=await post('/api/v3/calculate',{state:raw.v3});cleanV3=checked.state;}
    // No API keys, executable content or third-party files are ever restored.
    const records={'md-reborn-watch':watch,'md-reborn-names':names,'md-reborn-notes':notes,'md-reborn-reports':Array.isArray(raw.reports)?normaliseLocalReports(raw.reports):[]};
    if(cleanV3)records['md-reborn-v3']=cleanV3;
    if(cleanDrafts)records['md-analyst-drafts-v35']=cleanDrafts;
    if(raw.design&&typeof AppDesign!=='undefined')records['md-reborn-design-v28']=AppDesign.normalise(raw.design);
    if(raw.preferences&&typeof raw.preferences==='object')records['md-reborn-workstation-v1']=raw.preferences;
    if(safeSymbol(raw.tapeSymbol||''))records['md-tape-symbol']=raw.tapeSymbol;
    if(cleanPaper)records['md-reborn-portfolio']=cleanPaper;
    commitBrowserRecords(records);
    E.watch=watch;E.names={...STOCK_NAMES,...names};E.notes=notes;E.editIndex=null;
    if(typeof reportsOnView==='function')reportsOnView();
    E.chartPoints=[];E.chartForecast=null;E.candles.clear();E.forecastNews.clear();E.fundamentals.clear();E.news=null;
    E.selected=E.watch[0]||'';renderAll();renderNotes();loadChart();resubscribe();autoQuoteCycle();
    window.dispatchEvent(new Event('marketdesk:workspace-restored'));
    queueWorkspaceBackup();
    toast('Research backup imported. Quotes and trade history will continue to load from Finnhub and local records.');
  }catch(e){toast('Backup import failed: '+e.message)}
  finally{$('import-workspace').value=''}
}
async function runLocalAudit(){
  const btn=$('local-audit-run'),out=$('local-audit-output');
  btn.disabled=true;out.textContent='Checking database, saved files and application assets…';
  try{
    const result=await api('/api/selftest');
    out.replaceChildren();
    for(const check of result.checks){
      const line=document.createElement('div');line.className='audit-line';
      const title=document.createElement('strong');title.textContent=(check.ok?'✓ ':'✕ ')+check.name;
      const detail=document.createElement('span');detail.textContent=check.detail;
      line.append(title,detail);out.appendChild(line);
    }
    const note=document.createElement('p');note.textContent=result.notice;out.appendChild(note);
  }catch(e){out.textContent='Local integrity audit failed: '+e.message}
  finally{btn.disabled=false}
}
let searchTimer,marketSearchRequest=0;
async function searchStocks(q){
 const seq=++marketSearchRequest,pane=$('search-results');q=q.trim();if(!q){pane.classList.add('hidden');return}
 pane.classList.remove('hidden');const local=localStockMatches(q);
 const render=(rows,note='')=>{pane.innerHTML=rows.map(x=>{const sym=String(x.symbol).toUpperCase();return `<div class="search-result"><div><strong>${escapeHtml(sym)} · ${escapeHtml(x.description||sym)}</strong><small>${escapeHtml(x.type||'Stock')} · ${escapeHtml(x.displaySymbol||sym)}</small></div><button data-add="${escapeHtml(sym)}" data-name="${escapeHtml(x.description||sym)}">${E.watch.includes(sym)?'OPEN':'+ ADD'}</button></div>`}).join('')+(note?`<p>${escapeHtml(note)}</p>`:'');};
 render(local,E.configured?'Searching Finnhub for more stocks…':'Add a Finnhub key in Settings for more search results and prices.');
 if(!E.configured)return;
 const alias=local.some(x=>x.symbol==='TTWO')&&(STOCK_ALIASES.TTWO||[]).some(x=>x.toUpperCase()===q.toUpperCase());
 try{const data=await api('/api/search?q='+encodeURIComponent(alias?'TTWO':q));if(seq!==marketSearchRequest)return;const seen=new Set(local.map(x=>x.symbol));const remote=(data.result||[]).filter(x=>{const sym=String(x.symbol||'').toUpperCase();if(!safeSymbol(sym)||seen.has(sym))return false;seen.add(sym);return true;});const list=[...local,...remote].slice(0,18);render(list,list.length?'':'No matching stocks. Check the name or stock symbol.');}
 catch(e){if(seq===marketSearchRequest)render(local,'More search results are unavailable: '+e.message);}
}

function newsCards(items,mini=false){const valid=(items||[]).filter(n=>n.headline&&validHttpLink(n.url)).slice(0,mini?4:30);if(!valid.length)return `<div class="empty-state"><span>▤</span><h3>No verified headlines available</h3><p>News may be restricted by your plan or temporarily unavailable.</p></div>`;return valid.map(n=>{let stamp=n.datetime?fmtDateTime(n.datetime*1000):'Date not provided';let src=escapeHtml(n.source||'Unspecified source'),headline=escapeHtml(n.headline),link=escapeHtml(validHttpLink(n.url));return mini?`<div class="news-mini-item"><small>${src}  ·  ${stamp}</small><a href="${link}" target="_blank" rel="noopener noreferrer">${headline} ↗</a></div>`:`<article class="news-card"><div class="news-meta">${src}  ·  ${stamp}</div><h3>${headline}</h3><p>${escapeHtml((n.summary||'').slice(0,230))}</p><a href="${link}" target="_blank" rel="noopener noreferrer">Read original article ↗</a></article>`}).join('')}
async function loadNews(force=false){
  const id=++newsReq,sym=safeSymbol(E.selected)?E.selected:'';
  const saved='/api/saved-news'+(sym?'?symbol='+encodeURIComponent(sym):'');
  const live=force&&E.configured?(sym?'/api/news?symbol='+encodeURIComponent(sym):'/api/news'):saved;
  try{
    let result=await api(live).catch(()=>id===newsReq?api(saved):{items:[]});
    if(id!==newsReq||sym!==(safeSymbol(E.selected)?E.selected:''))return;
    E.news=result.items||[];
    if(!E.news.length)$('news-content').innerHTML='<div class="empty-state"><h3>No saved headlines'+(sym?' for '+escapeHtml(sym):'')+'</h3><p>'+(sym?'This company has no headlines saved on this Mac. ':'')+'Refresh news asks the free Finnhub feed for the last 7 days. If the plan does not include that company, nothing is invented.</p></div>';
    else renderNews();
  }catch(error){
    if(E.news)renderNews();
    else $('news-content').innerHTML='<p>Saved news could not be read. '+escapeHtml(error.message)+'</p>';
  }
}
function renderNews(){if(E.news){$('news-content').innerHTML=newsCards(E.news);$('overview-news').innerHTML=newsCards(E.news,true)}}
async function loadCompany(){const id=++companyReq;let sym=$('company-select').value||E.selected;if(!sym){$('company-content').textContent='Add a stock to your watchlist to see company details.';return}if(!E.configured){$('company-content').innerHTML='<div class="empty-state"><h3>Connect Finnhub first</h3></div>';return}if(E.fundamentals.has(sym)){if(id===companyReq)showCompany(sym,E.fundamentals.get(sym));return}$('company-content').innerHTML='<div class="empty-state"><h3>Loading genuine company information…</h3></div>';try{const data=await api('/api/company?symbol='+encodeURIComponent(sym));if(id!==companyReq||($('company-select').value||E.selected)!==sym)return;data.retrievedAt=Number(data.retrieved_at)||Date.now();data.clientReceivedAt=Date.now();E.fundamentals.set(sym,data);showCompany(sym,data)}catch(e){if(id===companyReq&&$('company-select').value===sym)$('company-content').innerHTML=`<div class="empty-state"><h3>Company data unavailable</h3><p>${escapeHtml(e.message)}</p></div>`}}
function showCompany(sym,data){if($('company-select').value!==sym)return;const p=data.profile||{},metrics=data.metrics?.metric||{},name=p.name||safeName(sym),q=quoteFor(sym);if(p.name)E.names[sym]=p.name;let kv=[['Exchange',p.exchange],['Industry',p.finnhubIndustry],['Website',p.weburl],['IPO date',p.ipo],['Currency',p.currency],['Headquarters',p.country]];let metricValues=[['Market cap',p.marketCapitalization?('$'+fmtNum(p.marketCapitalization/1000,2)+'bn'):'Unavailable'],['P/E ratio',metrics.peBasicExclExtraTTM??metrics.peTTM],['52-week high',metrics['52WeekHigh']],['52-week low',metrics['52WeekLow']],['Dividend yield',metrics.dividendYieldIndicatedAnnual]];const logo=validHttpLink(p.logo);$('company-content').innerHTML=`<div class="surface company-hero">${logo?`<img class="company-logo" alt="" src="${escapeHtml(logo)}">`:'<span class="symbol-avatar" style="width:60px;height:60px;font-size:18px">'+escapeHtml(sym.slice(0,2))+'</span>'}<div><h2>${escapeHtml(name)}</h2><p>${escapeHtml(sym)}  ·  ${escapeHtml(p.exchange||'Exchange unreported')}  ·  ${escapeHtml(p.finnhubIndustry||'Sector not provided')}</p><p>Latest quote: ${q?fmtUnit(sym,q.p)+' · '+fmtDateTime(q.t):'Not received'}</p></div></div><div class="company-metrics">${metricValues.slice(0,4).map(([label,value])=>`<div class="metric-card"><span>${escapeHtml(label)}</span><strong>${value===undefined||value===null||value===''?'Unavailable':escapeHtml(value)}</strong></div>`).join('')}</div><div class="surface company-about"><h3>Company profile</h3><div class="kv">${kv.map(([label,value])=>`<div><span>${escapeHtml(label)}</span><strong>${value?escapeHtml(value):'Not available'}</strong></div>`).join('')}</div><p>Company market value and financial ratios may have different dates from the price quote. Company details may be old or missing from your plan. ${data.metrics_error?'Metrics provider note: '+escapeHtml(data.metrics_error):''}</p><p>Primary source: Finnhub /stock/profile2 and /stock/metric. Missing figures are not guessed.</p></div>`}
function timeWindow(range){const day=86400000;return ({'1H':1/24,'1D':1,'1W':7,'1M':30,'3M':90,'6M':183,'1Y':365,'2Y':730,'5Y':1826,'10Y':3653}[range]||1)*day}
function forecastHorizon(range){return ({'1W':5,'1M':10,'3M':20,'1Y':60,'2Y':60,'5Y':60,'10Y':60,'6M':30})[range]||0}
function setChartRange(range){
  if(!['1H','1D','1W','1M','3M','6M','1Y','2Y','5Y','10Y'].includes(range))return;
  resetSessionReplay();
  E.heatmapWindow=null;E.forecastFocus=false;E.range=range;E.chartPoints=[];E.chartForecast=null;E.chartSource='Loading your chosen period';window.Chart43?.backToLive();window.Move44?.clear();
  document.querySelectorAll('#overview-ranges button').forEach(el=>el.classList.toggle('active',el.dataset.range===range));
  $('chart-data-coverage').textContent='Loading '+range+' past prices…';drawChart();loadChart();
}
let chartReq=0,sessionRequest=0,newsReq=0,companyReq=0;

function resetSessionReplay(){
  sessionRequest++;
  E.sessionReplay=null;
  const button=$('chart-session38'),status=$('chart-session38-status');
  if(button){button.disabled=false;button.textContent='Load last available US date';}
  if(status)status.textContent='';
}

async function toggleSessionReplay(){
  if(E.sessionReplay){resetSessionReplay();loadChart();return;}
  const symbol=E.selected,button=$('chart-session38'),status=$('chart-session38-status');
  if(!DIRECTORY_BY_SYMBOL[symbol]){status.textContent='Choose a company in the US stock directory.';return;}
  const id=++sessionRequest;
  button.disabled=true;status.textContent='Checking saved and available Massive minute bars…';
  try{
    const data=await api('/api/v3/equity-session?symbol='+encodeURIComponent(symbol));
    if(id!==sessionRequest||symbol!==E.selected)return;
    if(!data.points?.length)throw Error(data.notice||'No available minute history.');
    E.sessionReplay=data;E.heatmapWindow=null;
    if(!['1H','1D'].includes(E.range))E.range='1D';
    document.querySelectorAll('#overview-ranges button').forEach(el=>el.classList.toggle('active',el.dataset.range===E.range));
    button.textContent='Return to recorded prices';
    status.textContent='Showing '+data.day+' New York time · '+(data.status==='saved'?'saved ':'')+'Massive minute bars.';
    loadChart();
  }catch(error){
    if(id===sessionRequest)status.textContent=error.message;
  }finally{
    if(id===sessionRequest)button.disabled=false;
  }
}

function renderSessionReplay(replay){
  const rows=ChartResearch.normaliseDaily(replay.points).map(point=>({...point,source:'massive_minute'}));
  const end=rows.at(-1)?.t||Date.now();
  const cutoff=E.range==='1H'?end-3600000:(rows[0]?.t||end)-60000;
  E.chartPoints=rows.filter(point=>point.t>cutoff);
  E.chartDomain={from:cutoff,to:end,range:E.range};
  E.savedSession=false;E.chartForecast=null;
  E.chartSource='MASSIVE · '+replay.day+' NEW YORK DATE';
  E.lastHistoryStatus='Massive split-adjusted minute history';
  $('chart-data-coverage').textContent=(replay.coverage?ChartResearch.describeCoverage(replay.coverage)+' · ':'')+E.chartPoints.length+' minute closes · '+replay.day+' New York date'+(E.range==='1H'?' · final recorded hour':'');
  $('overview-chart-note').textContent='Completed date from Massive. Includes any extended-hours bars supplied by the provider. The latest Finnhub quote is displayed separately.';
  const analysis=$('mdi-chart');if(analysis)analysis.textContent='';
  forecastStatus('Historical minute closes from Massive.');
  renderOverview();drawChart();if(typeof Desk!=='undefined')Desk.historyChanged();
}

const pendingHistory=new Map();
let historyRevision=0;
async function historicalFor(sym,range=E.range,useImported=true,refreshDaily=false){
  const years=range==='10Y'?10:range==='5Y'?5:range==='2Y'?2:1;
  const cacheKey=sym+':'+years+(useImported?':chart':':provider'),revision=historyRevision;
  // Reuse the same daily request across ranges with the same required depth.
  // Massive daily EOD takes priority when configured; Finnhub handles live data.
  // A short-lived denied/no-data response also avoids retry storms on free plans.
  const cached=E.candles.get(cacheKey);
  const cacheAge=cached?.status==='ok'?900000:(cached?.kind==='massive_local_budget'||cached?.kind==='massive_rate_limit'?45000:120000);
  if(!refreshDaily&&cached&&nowMs()-cached.savedAt<cacheAge)return cached;
  if(pendingHistory.has(cacheKey))return pendingHistory.get(cacheKey);
  const request=(async()=>{
    try{
      const imported=useImported?await api('/api/imported-history?symbol='+encodeURIComponent(sym)):{status:'no_data'};
      if(imported.status==='ok'){
        const state={...imported,savedAt:nowMs(),points:ChartResearch.normaliseDaily(imported.points),cached:true,message:'User-imported daily prices; not independently verified.'};
        if(revision===historyRevision){E.candles.set(cacheKey,state);if(useImported)E.candles.set(sym,state);}return state;
      }
      // Free Massive clips this request to its two-year entitlement. Longer
      // requests never silently claim to cover five or ten years.
      const end=Math.floor(nowMs()/1000),from=end-(years===1?430:Math.ceil(years*365.25)+2)*86400;
      const query=`?symbol=${encodeURIComponent(sym)}&resolution=D&from=${from}&to=${end}${refreshDaily?'&refresh=1':''}`;
      // Chart opening is local-first, even with keys configured. Refresh is explicit.
      // Forecast research keeps its existing provider path and source separation.
      let res;
      if(useImported&&!refreshDaily){
        try{res=await api('/api/saved-daily'+query)}catch{/* Try the existing provider route only if no saved response is readable. */}
      }
      if(res?.status!=='ok'){
        const historyPath=!E.massiveConfigured&&!E.configured?'/api/saved-daily':'/api/candles';
        try{res=await api(historyPath+query)}catch(error){
          const saved=await api('/api/saved-daily'+query).catch(()=>null);
          if(saved?.status==='ok')res={...saved,refresh_error:error.message};else throw error;
        }
        if(res.status!=='ok'){
          const saved=await api('/api/saved-daily'+query).catch(()=>null);
          if(saved?.status==='ok')res={...saved,refresh_error:res.message||'New prices unavailable'};
        }
      }
      let state={savedAt:nowMs(),status:res.status||'no_data',points:[],message:res.message||'',symbol:sym,provider:res.provider||(E.massiveConfigured?'massive':'finnhub'),source:res.source||'',cached:Boolean(res.cached),refreshError:res.refresh_error||'',notice:res.notice||'',kind:res.kind||'',coverage:res.coverage||null};
      if(res.status==='ok'&&res.candles){
        const c=res.candles;
        state.points=ChartResearch.normaliseDaily((c.t||[]).map((ts,i)=>({t:Number(ts)*1000,p:Number(c.c?.[i])})));
        state.status=state.points.length?'ok':'no_data';
      }
      if(revision===historyRevision){E.candles.set(cacheKey,state);if(useImported)E.candles.set(sym,state);}return state;
    }catch(e){const state={savedAt:nowMs(),status:'error',points:[],message:e.message,symbol:sym};if(revision===historyRevision){E.candles.set(cacheKey,state);if(useImported)E.candles.set(sym,state);}return state}
    finally{if(pendingHistory.get(cacheKey)===request)pendingHistory.delete(cacheKey)}
  })();
  pendingHistory.set(cacheKey,request);return request;
}
async function forecastHeadlines(sym){
  if(!E.configured)return {items:[],available:false};
  const hit=E.forecastNews.get(sym);
  if(hit&&nowMs()-hit.savedAt<420000)return hit;
  try{
    const response=await api('/api/news?symbol='+encodeURIComponent(sym));
    const entry={savedAt:nowMs(),items:(response.items||[]).slice(0,36),message:'',available:true};
    E.forecastNews.set(sym,entry);return entry;
  }catch(e){const entry={savedAt:nowMs(),items:[],message:e.message,available:false};E.forecastNews.set(sym,entry);return entry}
}
function forecastStatus(note,active=false){const el=$('chart-forecast-legend');if(el){el.textContent=note;el.classList.toggle('active',active)}}
function coverageStatus(points,cutoff,end,rawCount){
  const result=ChartResearch.coverage(points,cutoff,end);
  if(!result.count)return '0 recorded prices in '+E.range;
  const earliest=new Date(result.first).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
  const latest=new Date(result.last).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
  return `${result.count} recorded prices · ${earliest} – ${latest}${rawCount>result.count?' · filtered for '+(E.heatmapWindow?.label||E.range):''}`;
}
async function loadChart(fetchHistorical=true,refreshDaily=false){
  if(!E.selected){E.chartPoints=[];E.chartForecast=null;E.chartSource='No stock selected';drawChart();return}
  const id=++chartReq,sym=E.selected,range=E.range;
  if(E.sessionReplay?.symbol===sym){renderSessionReplay(E.sessionReplay);return;}
  let end=nowMs(),cutoff=end-timeWindow(range),savedSession=false;
  if(E.heatmapWindow){cutoff=Date.parse(E.heatmapWindow.start+'T00:00:00Z');end=Date.parse(E.heatmapWindow.end+'T23:59:59Z');}
  E.chartDomain={from:cutoff,to:end,range};
  E.chartForecast=null;
  let local=[],localCoverage=null;
  try{const r=await api('/api/history?symbol='+encodeURIComponent(sym)+'&since='+Math.floor(cutoff));local=r.points||[];localCoverage=r.coverage||null}
  catch(e){console.warn('Local chart records unavailable:',e.message)}
  if(id!==chartReq||sym!==E.selected||range!==E.range)return;
  let historical=E.candles.get(sym);
  if(!['1H','1D'].includes(range) && fetchHistorical)historical=await historicalFor(sym,range,true,refreshDaily);
  if(id!==chartReq||sym!==E.selected||range!==E.range)return;
  const valid=x=>Number.isFinite(x.t)&&Number.isFinite(x.p)&&x.p>0&&x.p<=1e9&&x.t>=cutoff&&x.t<=end+60000;
  let actual=local.map(x=>({t:Number(x.t),p:Number(x.p),source:x.source})).filter(valid);
  if(['1H','1D'].includes(range)&&!actual.length){
    // An empty present-day window after sleep is not deletion. Recover the last
    // recorded session with its real dates; never shift prices to today's time.
    try{
      const saved=await api('/api/history?symbol='+encodeURIComponent(sym)+'&since=0');
      if(id!==chartReq||sym!==E.selected||range!==E.range)return;
      const past=(saved.points||[]).map(x=>({t:Number(x.t),p:Number(x.p),source:x.source})).filter(x=>Number.isFinite(x.t)&&x.t>0&&x.t<=end&&Number.isFinite(x.p)&&x.p>0&&x.p<=1e9).sort((a,b)=>a.t-b.t);
      if(past.length){end=past.at(-1).t;cutoff=end-timeWindow(range);actual=past.filter(valid);local=past;savedSession=true;E.chartDomain={from:cutoff,to:end,range};}
    }catch(error){console.warn('Saved session unavailable:',error.message)}
  }
  let source='LOCALLY RECORDED FINNHUB OBSERVATIONS';
  const haveDaily=!['1H','1D'].includes(range)&&historical?.status==='ok'&&historical.points?.length;
  if(haveDaily){
    // Never splice locally recorded minute-level observations into historical DAILY
    // candles. When the computer sleeps, the local record has gaps; blending the
    // two frequencies previously created spikes/triangles that looked like prices.
    // The separately displayed latest Finnhub quote is intentionally NOT a candle.
    const candleSource=historical.provider==='imported'?'user_imported_daily':historical.provider==='massive'?'massive_daily':'finnhub_candle';
    actual=historical.points.filter(valid).map(x=>({...x,source:candleSource}));
    source=historical.provider==='imported'?'IMPORTED DAILY PRICES · UNVERIFIED':historical.provider==='massive'?'MASSIVE EOD DAILY CLOSES (SPLIT-ADJUSTED)':'FINNHUB HISTORICAL DAILY CLOSES';
    if(historical.provider==='massive'&&historical.cached)source+=' · VERIFIED LOCAL CACHE';
  }else if(['1H','1D'].includes(range)){
    // Finnhub WebSocket trades and current quote may extend the *local* 1D
    // observations, but never pretend to backfill the Mac's offline periods.
    const lastTrade=E.trades.get(sym);
    if(lastTrade&&lastTrade.t>=cutoff)actual.push({t:lastTrade.t,p:lastTrade.p,source:'finnhub_websocket'});
    const quote=E.quotes.get(sym)?.quote;
    if(quote&&quote.t*1000>=cutoff)actual.push({t:quote.t*1000,p:quote.c,source:'finnhub_quote'});
  }
  actual=actual.filter(valid).sort((a,b)=>a.t-b.t);
  const unique=[];
  for(const pt of actual){
    if(unique.length&&unique[unique.length-1].t===pt.t){
      if(pt.source==='finnhub_websocket'||unique[unique.length-1].source!=='finnhub_websocket')unique[unique.length-1]=pt;
    }else unique.push(pt);
  }
  E.savedSession=savedSession;E.chartPoints=unique.slice(-5000);E.chartSource=source+(savedSession?' · LAST SAVED SESSION · NOT CURRENT':'');
  if(window.Chart43&&!Chart43.fits(E.chartPoints)){Chart43.backToLive();E.chartSource+=' · previous window had no prices here, so the full period is shown';}
  E.lastHistoryStatus=['1H','1D'].includes(range)?'Intraday: local verified observations only':
    historical?.status==='ok'?(historical.provider==='imported'?'User-imported daily prices (unverified)':historical.provider==='massive'?(historical.refreshError?'Massive cached history · refresh unavailable':'Massive historical daily bars received (EOD)'):'Finnhub historical closes received'):
    historical?.status==='entitlement'?'Price history is not included in your plan':
    historical?.status==='error'?'Historical request failed':
    'No verified daily historical candles available';
  $('diag-candles').textContent=E.lastHistoryStatus;
  const segments=ChartResearch.chartSegments(E.chartPoints,range);
  const offlineGapCount=Math.max(0,segments.length-1);
  const coveragePacket=haveDaily?historical?.coverage:localCoverage;
  $('chart-data-coverage').textContent=(coveragePacket?ChartResearch.describeCoverage(coveragePacket)+' · ':'')+coverageStatus(E.chartPoints,cutoff,end,local.length+(historical?.points?.length||0))+(['1H','1D'].includes(range)&&offlineGapCount?' · '+offlineGapCount+' unrecorded gap'+(offlineGapCount===1?'':'s'):'');
  const coverage=ChartResearch.coverage(E.chartPoints,cutoff,end);
  const incomplete=coverage.count<2 || (!['1H','1D'].includes(range)&&(coverage.first>cutoff+14*86400000||coverage.last<end-10*86400000));
  if(incomplete&&!['1H','1D'].includes(range))$('chart-data-coverage').textContent+=' · Partial '+range+' history';
  if(historical?.provider==='imported'&&!['1H','1D'].includes(range))$('chart-data-coverage').textContent+=' · Imported, not independently verified'+(historical.split_adjusted?'':' · Unadjusted: splits may cause jumps');
  let note=coverage.count===0?'No recorded prices are available for this period.':
    coverage.count===1?'One price recorded. More prices are needed to show a trend.':
    historical?.provider==='imported'?'User-imported daily prices from '+historical.source+'. '+(historical.split_adjusted?'You marked these as split-adjusted.':'Not split-adjusted: stock splits can look like price rises or falls.')+' The file is not independently verified. Daily dates are session labels, not intraday timestamps. No provider data or live quotes are mixed into this line.':
    source.startsWith('MASSIVE')?'Daily closing prices from Massive, adjusted for stock splits. Massive records these even when your Mac is off. The Finnhub price quote above is shown separately.':
    source.startsWith('FINNHUB')?'Daily closing prices from Finnhub. The latest price quote above is separate from this past data.':
    'Hourly and 24-hour charts only record prices while Market Desk is running. When your Mac is off or asleep, missing periods stay as gaps. Choose 1M or 1Y for daily prices recorded by Massive.';
  if(['1H','1D'].includes(range)&&offlineGapCount)note+=' '+offlineGapCount+' recording gap'+(offlineGapCount===1?'':'s')+' detected; no intermediate prices invented.';
  if(['1H','1D'].includes(range)&&coverage.count<2)note+=' This chart only shows prices recorded while Market Desk was running. Choose 1M or 1Y for daily prices recorded by a provider.';
  if(incomplete && !['1H','1D'].includes(range))note+=' SOME HISTORY IS MISSING: this is not a complete '+range+' history.';
  if(['5Y','10Y'].includes(range)&&historical?.provider==='massive')note+=' Massive Basic supplies about 2 years. Import a longer daily-price CSV below for this range.';
  if(historical?.notice)note+=' '+historical.notice;
  if(historical?.refreshError)note+=' Showing saved price history because new data could not be loaded. '+historical.refreshError;
  if(!['1H','1D'].includes(range)&&historical?.status!=='ok')note+=' '+(historical?.message||(E.massiveConfigured?'Massive historical data is unavailable. Check Settings.':'Finnhub historical access is unavailable. Add a Massive key in Settings to load real US daily closes.'));
  if(savedSession){note='LAST SAVED SESSION: '+new Date(cutoff).toLocaleString('en-GB')+' to '+new Date(end).toLocaleString('en-GB')+'. No prices were recorded in the current '+(range==='1H'?'hour':'24 hours')+'. These are genuine older recordings, not live prices or a backfill of time while the Mac was off. Intelligence’s current-hour/day overview remains separate. '+note;$('chart-data-coverage').textContent='Last saved session · '+$('chart-data-coverage').textContent;}
  $('overview-chart-note').textContent=note;
  // Draw the saved closes before the forecast check. The check can take longer than the chart read.
  renderOverview();drawChart();window.Look43?.refresh();
  if(id!==chartReq||sym!==E.selected||range!==E.range)return;
  if(!E.forecastEnabled){forecastStatus('The forecast line is off. Past prices are still shown.');}
  else if(['1H','1D'].includes(range)){forecastStatus('Hourly and 24-hour charts show recorded prices only. Choose a longer period for the daily-close forecast.');}
  else if(historical?.provider==='imported'){forecastStatus('Forecast off for imported files: these prices have not been independently verified.');}
  else{
    forecastStatus('Checking saved closes for '+sym+'…');
    try{
      const packet=await api('/api/v3/forecast61?symbol='+encodeURIComponent(sym));
      if(id!==chartReq||sym!==E.selected||range!==E.range)return;
      if(packet.status==='learned'&&packet.rows&&packet.rows.length>1){
        E.chartForecast=packet;
        forecastStatus((packet.anchorDate?'Last close '+packet.anchorDate+'. ':'')+packet.notice,true);
      }else{
        E.chartForecast=null;
        forecastStatus((packet.anchorDate?'Last close '+packet.anchorDate+'. ':'')+(packet.notice||packet.error||'No purple line is drawn.'));
      }
    }catch(error){
      E.chartForecast=null;
      forecastStatus('Forecast check unavailable. '+error.message);
    }
  }
  renderOverview();drawChart();if(typeof Desk!=='undefined')Desk.historyChanged();if(typeof MDI!=='undefined')MDI.chart();
}
function drawChart(){
  const isLight=document.documentElement?.dataset?.theme==='light';
  const canvas=$('overview-chart');if(!canvas||!canvas.getClientRects().length)return;
  const rect=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);
  if(rect.width<10)return;
  const pixelWidth=Math.round(rect.width*dpr),pixelHeight=Math.round(rect.height*dpr);
  if(canvas.width!==pixelWidth)canvas.width=pixelWidth;
  if(canvas.height!==pixelHeight)canvas.height=pixelHeight;
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  const w=rect.width,h=rect.height,pad={left:12,right:67,top:22,bottom:29};
  const pw=w-pad.left-pad.right,ph=h-pad.top-pad.bottom;
  ctx.clearRect(0,0,w,h);
  if(pw<=0||ph<=0)return;
  const loaded=E.chartPoints.filter(p=>Number.isFinite(p.t)&&Number.isFinite(p.p));
  const replaying=Boolean(window.Replay43?.active);
  const base=replaying?Replay43.prices():loaded;
  const lens=window.Chart43?.lens(base);
  const points=(lens?lens.points:base).filter(p=>Number.isFinite(p.t)&&Number.isFinite(p.p));
  if(typeof MarketTruth36!=='undefined')MarketTruth36.updateLabel(E.selected);
  const plottedLabel=$('chart-observed-summary');if(plottedLabel){
    const first=points[0],last=points.at(-1),change=points.length>1?(last.p/first.p-1)*100:null;
    const date=t=>new Date(t).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
    plottedLabel.textContent=change!==null?`${E.savedSession?'Last saved session · ':''}${change>=0?'↑ Up':'↓ Down'} ${Math.abs(change).toFixed(2)}% between the displayed prices · ${fmtUnit(E.selected,first.p)} (${date(first.t)}) → ${fmtUnit(E.selected,last.p)} (${date(last.t)}) · ${E.heatmapWindow?'completed-session close-to-close return for the selected heatmap period':'change within this displayed range, NOT the full-session previous-close return'}; no separate dividends added. Missing history is not counted.`:points.length?'Only one recorded price; no change can be calculated.':'No prices plotted for this period.';
  }
  const forecast=!replaying&&E.forecastEnabled&&!['1H','1D'].includes(E.range)?E.chartForecast:null;
  const focus=Boolean(forecast?.rows?.length&&E.forecastFocus);
  const focusButton=$('chart-forecast-focus');
  if(focusButton){
    focusButton.disabled=!forecast?.rows?.length;
    focusButton.setAttribute('aria-pressed',String(focus));
    focusButton.textContent=focus?'Show full chart and range':'Focus on purple line';
  }
  if(focus&&plottedLabel){
    const first=forecast.rows[0],last=forecast.rows.at(-1);
    const move=(last.price/first.price-1)*100;
    plottedLabel.textContent='Scenario centre detail · '+fmtPct(move)+' over '+last.day+' sessions. The full chart shows the uncertainty range.';
  }
  const segments=focus?[]:ChartResearch.chartSegments(points,E.range);
  const from=lens?.from??(E.chartDomain?.from||nowMs()-timeWindow(E.range)),to=lens?.to??(E.chartDomain?.to||nowMs());
  const histW=focus?0:pw*(forecast?.rows?.length ? .68 : 1);
  const X=t=>pad.left+Math.max(0,Math.min(1,(t-from)/(to-from||1)))*histW;
  const divide=forecast?X(forecast.anchor.t):pad.left+histW;
  const FX=d=>divide+(w-pad.right-divide)*d/Math.max(1,forecast?.rows?.at(-1).day||1);
  if(!points.length){
    ctx.fillStyle='#91a3b3';ctx.font='12px -apple-system, sans-serif';ctx.textAlign='center';
    ctx.fillText('No recorded prices for '+E.range+' · review data coverage below',w/2,h/2);
    $('overview-tooltip').classList.add('hidden');return;
  }
  const sessionReference=!replaying&&!E.sessionReplay&&typeof MarketTruth36!=='undefined'?MarketTruth36.context(E.selected,points):null;
  const values=focus?forecast.rows.map(row=>row.price):points.map(p=>p.p);
  if(!focus&&sessionReference)values.push(sessionReference.previous);
  if(!focus&&forecast)for(const row of forecast.rows)values.push(row.low,row.high);
  const candleBars=!focus&&window.Look43?.candleBars?Look43.candleBars(from,to):null;
  if(candleBars)for(const bar of candleBars)values.push(bar.l,bar.h);
  let min=Math.min(...values),max=Math.max(...values);
  const span=Math.max((max-min)*.14,max*(focus ? .00005 : .001),.01);min-=span;max+=span;
  const Y=p=>pad.top+(1-(p-min)/(max-min))*ph;
  ctx.lineWidth=1;ctx.font='11px -apple-system, sans-serif';ctx.textAlign='right';
  for(let i=0;i<=4;i++){
    const yy=pad.top+i*ph/4;
    ctx.strokeStyle=isLight?'#dce3ed':'#233852';ctx.beginPath();ctx.moveTo(pad.left,yy);ctx.lineTo(w-pad.right+3,yy);ctx.stroke();
    ctx.fillStyle=isLight?'#53657d':'#9eb6d6';ctx.fillText((max-(max-min)*i/4).toFixed(2),w-4,yy+4);
  }
  const dateLabel=t=>['1H','1D'].includes(E.range)?new Date(t).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'}):new Date(t).toLocaleDateString('en-GB',(['1Y','2Y','5Y','10Y'].includes(E.range)?{month:'short',year:'numeric'}:{day:'numeric',month:'short'}));
  ctx.textAlign='center';ctx.fillStyle=isLight?'#53657d':'#9eb6d6';
  if(!focus)for(const factor of [0,.25,.5,.75,1]){
    const stamp=from+(to-from)*factor;
    ctx.fillText(dateLabel(stamp),pad.left+factor*histW,h-7);
    ctx.strokeStyle='#263c542d';ctx.setLineDash([2,6]);ctx.beginPath();ctx.moveTo(pad.left+factor*histW,pad.top);ctx.lineTo(pad.left+factor*histW,h-pad.bottom);ctx.stroke();ctx.setLineDash([]);
  }
  if(forecast){
    ctx.fillStyle='#a88de10e';ctx.fillRect(divide,pad.top,w-pad.right-divide,ph);
    ctx.strokeStyle='#8267b055';ctx.setLineDash([2,4]);ctx.beginPath();ctx.moveTo(divide,pad.top);ctx.lineTo(divide,h-pad.bottom);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=isLight?'#72539b':'#c6b4e4';ctx.font='9px -apple-system, sans-serif';ctx.textAlign='right';
    ctx.fillText((forecast.kind==='model'?'FORECAST':'SCENARIO')+' +'+forecast.rows.at(-1).day+' SESSIONS',w-pad.right-2,pad.top+9);
    const xr=row=>FX(row.day),yr=row=>Y(row.price);
    if(!focus){
      ctx.beginPath();forecast.rows.forEach((r,i)=>i?ctx.lineTo(xr(r),Y(r.high)):ctx.moveTo(xr(r),Y(r.high)));
      forecast.rows.slice().reverse().forEach(r=>ctx.lineTo(xr(r),Y(r.low)));
      ctx.closePath();ctx.fillStyle='#b38cff24';ctx.fill();
    }else{
      const lastDay=forecast.rows.at(-1).day;
      ctx.fillStyle=isLight?'#53657d':'#9eb6d6';ctx.textAlign='center';
      for(const day of [0,Math.round(lastDay/2),lastDay]){
        const label=day===0?'Last close':'+'+day+' sessions';
        const x=Math.max(pad.left+30,Math.min(w-pad.right-30,xr({day})));
        ctx.fillText(label,x,h-7);
      }
    }
    ctx.beginPath();forecast.rows.forEach((r,i)=>i?ctx.lineTo(xr(r),yr(r)):ctx.moveTo(xr(r),yr(r)));
    ctx.strokeStyle=isLight?'#8051b7':'#c59cff';ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.stroke();ctx.setLineDash([]);
    const last=forecast.rows.at(-1);ctx.fillStyle='#c59cff';ctx.beginPath();ctx.arc(xr(last),yr(last),3.5,0,Math.PI*2);ctx.fill();
  }
  if(!focus&&points.length===1){const p=points[0];ctx.fillStyle='#7aafff';ctx.beginPath();ctx.arc(X(p.t),Y(p.p),5,0,Math.PI*2);ctx.fill();}
  else if(!focus&&candleBars?.length){
    const slot=histW/Math.max(candleBars.length,1),width=Math.max(2,Math.min(9,slot*.62));
    for(const bar of candleBars){
      const x=X(bar.t),up=bar.c>=bar.o,colour=up?'#3dd68c':'#ff5d73';
      ctx.strokeStyle=colour;ctx.fillStyle=colour;ctx.lineWidth=1.2;
      ctx.beginPath();ctx.moveTo(x,Y(bar.h));ctx.lineTo(x,Y(bar.l));ctx.stroke();
      const top=Y(Math.max(bar.o,bar.c)),bottom=Y(Math.min(bar.o,bar.c));
      ctx.fillRect(x-width/2,top,width,Math.max(1,bottom-top));
    }
  }
  else if(!focus){
    const up=points.at(-1).p>=(sessionReference?sessionReference.previous:points[0].p),colour=up?(isLight?'#306bcb':'#7aafff'):(isLight?'#c23d59':'#ff8b9d');
    if(sessionReference){const baselineY=Y(sessionReference.previous);ctx.save();ctx.strokeStyle=isLight?'#65758b':'#b7c9df';ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(pad.left,baselineY);ctx.lineTo(w-pad.right,baselineY);ctx.stroke();ctx.fillStyle=isLight?'#52647b':'#b7c9df';ctx.fillText('Provider previous close',pad.left+4,baselineY-6);ctx.restore();}
    // Draw every continuous observed segment independently. Older versions
    // correctly split the stroke but NOT the filled area, making long periods
    // while the laptop slept look like dramatic price spikes. Never interpolate.
    const gradient=ctx.createLinearGradient(0,pad.top,0,h-pad.bottom);
    gradient.addColorStop(0,up?'#5495ff32':'#ff7f8824');gradient.addColorStop(1,'#10192100');
    for(const seg of segments){
      if(seg.length<2)continue;
      ctx.save();ctx.beginPath();ctx.moveTo(X(seg[0].t),h-pad.bottom);
      for(const p of seg)ctx.lineTo(X(p.t),Y(p.p));
      ctx.lineTo(X(seg.at(-1).t),h-pad.bottom);ctx.closePath();
      ctx.fillStyle=gradient;ctx.fill();ctx.restore();
      ctx.beginPath();seg.forEach((p,i)=>i?ctx.lineTo(X(p.t),Y(p.p)):ctx.moveTo(X(p.t),Y(p.p)));
      ctx.strokeStyle=colour;ctx.lineWidth=2.4;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
    }
    if(['1H','1D'].includes(E.range)){
      // Dot isolated genuine observations instead of drawing artificial lines.
      for(const seg of segments){if(seg.length!==1)continue;const p=seg[0];ctx.fillStyle=colour;ctx.beginPath();ctx.arc(X(p.t),Y(p.p),3,0,Math.PI*2);ctx.fill();}
      // Subtle visual acknowledgement of unrecorded periods (no synthetic ticks).
      const gaps=ChartResearch.chartGaps(points,E.range);
      for(const gap of gaps.slice(0,8)){
        const left=X(gap.from),right=X(gap.to);
        if(right-left<5)continue;
        ctx.fillStyle='#9ba9b50b';ctx.fillRect(left,pad.top,right-left,ph);
        ctx.strokeStyle='#92a4b755';ctx.setLineDash([2,5]);
        ctx.beginPath();ctx.moveTo(left,pad.top+2);ctx.lineTo(left,pad.top+ph-1);ctx.moveTo(right,pad.top+2);ctx.lineTo(right,pad.top+ph-1);ctx.stroke();ctx.setLineDash([]);
      }
    }
    const p=points.at(-1);ctx.fillStyle=colour;ctx.beginPath();ctx.arc(X(p.t),Y(p.p),3.5,0,Math.PI*2);ctx.fill();
  }
  if(window.Chart43)Chart43.paint(ctx,X,Y,points);
  if(E.chartHover!==null){
    const mx=E.chartHover;
    if(!focus&&mx<=divide){
      const pick=points.reduce((best,p)=>Math.abs(X(p.t)-mx)<Math.abs(X(best.t)-mx)?p:best,points[0]);
      const px=X(pick.t),py=Y(pick.p);
      ctx.strokeStyle='#91a5b3';ctx.lineWidth=1;ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(px,pad.top);ctx.lineTo(px,h-pad.bottom);ctx.moveTo(pad.left,py);ctx.lineTo(w-pad.right,py);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#bad5ff';ctx.beginPath();ctx.arc(px,py,4,0,Math.PI*2);ctx.fill();
      const tip=$('overview-tooltip');tip.classList.remove('hidden');
      tip.textContent=`OBSERVED · ${fmtUnit(E.selected,pick.p)} · ${fmtDateTime(pick.t)}`;
      tip.style.left=Math.max(0,Math.min(px-80,w-240))+'px';tip.style.top=Math.max(0,py-41)+'px';
    }else if(forecast && mx<=w-pad.right){
      const row=forecast.rows.reduce((best,r)=>Math.abs(FX(r.day)-mx)<Math.abs(FX(best.day)-mx)?r:best,forecast.rows[0]);
      const tip=$('overview-tooltip');tip.classList.remove('hidden');
      tip.textContent=`${forecast.kind==='model'?'MODEL':'SCENARIO'}, NOT OBSERVED · +${row.day} sessions · ${row.kind==='recorded'?'recorded close':'evaluated session'} ${fmtUnit(E.selected,row.price)} · band ${fmtUnit(E.selected,row.low)}–${fmtUnit(E.selected,row.high)}${forecast.interpolation&&forecast.interpolation.length?' · straight join between evaluated sessions':''}`;
      tip.style.left=Math.max(0,Math.min(mx-140,w-370))+'px';
      tip.style.top=Math.max(0,Y(row.price)-46)+'px';
    }else $('overview-tooltip').classList.add('hidden');
  }else $('overview-tooltip').classList.add('hidden');
}
let forecastRunId=0;
async function runForecast(){
  const id=++forecastRunId,sym=$('forecast-select').value;
  if(!sym)return;
  const pane=$('forecast-content');
  pane.innerHTML='<div class="empty-state"><h3>Checking the saved daily closes…</h3></div>';
  try{
    const packet=await api('/api/v3/forecast61?symbol='+encodeURIComponent(sym));
    if(id!==forecastRunId||sym!==$('forecast-select').value)return;
    if(packet.error)throw new Error(packet.error);
    const cards=(packet.horizons||[]).map(row=>`<div class="forecast-validation-card"><span>${row.horizon}-SESSION</span><strong>${escapeHtml(row.status)}</strong><p>${row.modelErrorPP!=null?`Model ${row.modelErrorPP.toFixed(2)} pp · unchanged ${row.baselineErrorPP.toFixed(2)} pp · ${row.testCases} later tests`:'Not enough separate later tests.'}</p></div>`).join('');
    const path=(packet.rows||[]).filter(row=>row.day>0).map(row=>`<div class="forecast-tile"><small>+${row.day} SESSIONS · EVALUATED</small><strong>${fmtUnit(sym,row.price)}</strong><p>Band ${fmtUnit(sym,row.low)} – ${fmtUnit(sym,row.high)}</p></div>`).join('')||'<div class="forecast-tile"><small>LEARNED PATH</small><strong>Withheld</strong><p>No horizon beat an unchanged price on the later tests.</p></div>';
    pane.innerHTML=`<div class="section-heading"><div><div class="section-tag">${escapeHtml(packet.method||'')} / ${escapeHtml(sym)}</div><h2>${packet.status==='learned'?'Evaluated forecast path':'Learned path withheld'}</h2></div></div>
      <div class="forecast-tiles">${path}</div>
      <div class="forecast-validation-grid">${cards}</div>
      <div class="surface forecast-explain"><p>${escapeHtml(packet.inputs||'')}</p><p>${escapeHtml(packet.trainingNote||'')} Observations ${packet.observations||0}, ${escapeHtml(packet.first||'—')} to ${escapeHtml(packet.anchorDate||'—')}.</p><p>${escapeHtml(packet.notice||'')}</p><p>${(packet.interpolation||[]).map(escapeHtml).join(' ')}</p><p>A typed company scenario stays separate from this price model. Issued forecast records are not replaced by this check. Count already saved: ${packet.issuedCount||0}.</p></div>`;
  }catch(e){
    if(id!==forecastRunId||sym!==$('forecast-select').value)return;
    pane.innerHTML=`<div class="empty-state"><span>⌁</span><h3>No forecast available</h3><p>${escapeHtml(e.message)}</p><p>Missing past prices are not made up. Check your Massive plan and request limit in Settings.</p></div>`;
  }
}
function renderNotes(){const pane=$('saved-notes');$('note-count').textContent=E.notes.length;pane.innerHTML=E.notes.length?E.notes.map((n,i)=>`<div class="note-item"><strong>${escapeHtml(n.title)}</strong><small>${escapeHtml(n.date)}</small><p>${escapeHtml((n.thesis||'').slice(0,260))}</p><div class="note-actions"><button data-editnote="${i}">Edit</button><button class="delete-note" data-deletenote="${i}">Delete</button></div></div>`).join(''):'<div class="empty-state"><span>▣</span><h3>Your research archive is empty</h3><p>Saved notes stay in this browser profile. Use Export to keep a portable copy.</p></div>';if(typeof Projects32!=='undefined')Projects32.notesChanged();}
function saveNote(){const title=$('note-title').value.trim();if(!title){toast('Add a company or research topic first.');return}const note={title,thesis:$('note-thesis').value,risk:$('note-risk').value,evidence:$('note-evidence').value,date:new Date().toLocaleString('en-GB')};if(Number.isInteger(E.editIndex)){E.notes[E.editIndex]=note;E.editIndex=null}else E.notes.unshift(note);saveJSON('md-reborn-notes',E.notes);renderNotes();for(const id of ['note-title','note-thesis','note-risk','note-evidence'])$(id).value='';toast('Research note saved on this browser')}
function exportNotes(){const text=E.notes.map(n=>`${n.title}\n${n.date}\n\nTHESIS\n${n.thesis}\n\nRISKS / CONTRARY EVIDENCE\n${n.risk}\n\nSOURCES\n${n.evidence}\n\n${'='.repeat(60)}\n`).join('\n');const blob=new Blob([text||'No saved notes yet.'],{type:'text/plain;charset=utf-8'});let url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='MarketDesk-Research-'+new Date().toISOString().slice(0,10)+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function saveMassiveToken(){
  const input=$('massive-api-key'),button=$('massive-save-key'),token=input.value.trim();
  if(!token){toast('Paste your private Massive API key in the field first.');return}
  button.disabled=true;
  try{
    await post('/api/massive-token',{token});
    input.value='';E.massiveConfigured=true;E.candles.clear();
    $('massive-key-state').textContent='SAVED PRIVATELY';
    $('massive-test-result').textContent='Key saved privately on this Mac. Click Test Massive daily history to check your plan’s access.';
    toast('Massive key saved locally. Finnhub live feed is unchanged.');
    if(E.forecastEnabled&&['1H','1D'].includes(E.range))setChartRange('1Y');else loadChart();
  }catch(e){$('massive-test-result').textContent='Could not save key: '+e.message;toast('Massive key was not saved')}
  finally{button.disabled=false}
}
async function clearMassiveToken(){
  try{
    await post('/api/massive-token',{clear:true});
    E.massiveConfigured=false;E.candles.clear();$('massive-api-key').value='';
    $('massive-key-state').textContent='NOT CONFIGURED';
    $('massive-test-result').textContent='Massive key removed. Finnhub remains configured independently.';
    toast('Massive historical-data key removed from this Mac');loadChart();
  }catch(e){toast('Cannot remove Massive key: '+e.message)}
}
async function testMassive(){
  const btn=$('massive-test'),out=$('massive-test-result');btn.disabled=true;
  out.textContent='Checking genuine AAPL daily bars with Massive (one request)…';
  try{
    const data=await api('/api/massive-diagnose');
    const next=data.retry_after?` Retry after at least ${data.retry_after} seconds without repeated requests.`:'';
    const detail=data.ok?` ${data.count} verified AAPL daily bars; most recent ${fmtDateTime(data.latest_bar_time_ms)} · ${data.latency_ms}ms.`:` [${data.kind||'provider_error'}]${next}`;
    out.textContent=(data.ok?'✓ ':'✕ ')+data.message+detail;
    out.className='diag-result '+(data.ok?'good':'issue');
    if(data.ok){E.candles.clear();if(E.forecastEnabled&&['1H','1D'].includes(E.range))setChartRange('1Y');else loadChart();}
  }catch(e){out.className='diag-result issue';out.textContent='Historical test failed: '+e.message}
  finally{btn.disabled=false}
}
async function saveToken(){let token=$('api-key').value.trim();try{await post('/api/token',{token});$('api-key').value='';E.configured=true;E.quotes.clear();E.quoteFailures.clear();E.quoteChecks.clear();E.trades.clear();E.verifiedAt=0;E.news=null;E.candles.clear();E.lastHistoryStatus='';E.lastQuoteError='';E.lastGoodQuoteAt=0;E.probe=null;E.fundamentals.clear();alertBanner('');renderAll();connectWS();await runDiagnostics();await autoQuoteCycle();loadNews();loadChart();toast('Finnhub token saved locally; check the connection result above')}catch(e){toast('Could not save token: '+e.message)}}
async function clearToken(){try{await post('/api/token',{clear:true});stopWS();E.configured=false;E.quotes.clear();E.quoteFailures.clear();E.quoteChecks.clear();E.trades.clear();E.verifiedAt=0;E.news=null;E.candles.clear();E.lastHistoryStatus='';E.lastQuoteError='';E.probe=null;E.lastGoodQuoteAt=0;renderAll();toast('Saved token removed from this Mac')}catch(e){toast('Could not clear key: '+e.message)}}
function attachEvents(){$('chart-forecast-focus').addEventListener('click',()=>{E.forecastFocus=!E.forecastFocus;E.chartHover=null;drawChart()});$('chart-session38').addEventListener('click',toggleSessionReplay);$('chart-refresh-saved').addEventListener('click',()=>{resetSessionReplay();E.heatmapWindow=null;if(['1H','1D'].includes(E.range)){E.range='1Y';document.querySelectorAll('#overview-ranges button').forEach(b=>b.classList.toggle('active',b.dataset.range==='1Y'));}E.candles.clear();loadChart(true,true)});setupHistoryImport();if(typeof PriceAlerts!=='undefined')PriceAlerts.setup();setupStockDirectory();setupMarketTabs();if(typeof setupResearchV18==='function')setupResearchV18();window.addEventListener('storage',e=>{if(e.key==='md-reborn-reports'&&typeof reportsOnView==='function')reportsOnView()});if(typeof setupResearchV17==='function')setupResearchV17();if(typeof setupV19==='function')setupV19();document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',()=>changeView(b.dataset.view)));$('open-settings').addEventListener('click',()=>changeView('settings'));$('menu-toggle').addEventListener('click',()=>$('sidebar').classList.toggle('open'));$('overview-explore').addEventListener('click',()=>changeView('markets'));$('chart-expand').addEventListener('click',toggleExpandedChart);if(typeof tapeSetup==='function')tapeSetup();$('refresh-overview').addEventListener('click',()=>loadQuotes(E.watch.slice(0,6)));$('markets-refresh').addEventListener('click',()=>autoQuoteCycle());$('markets-search-focus').addEventListener('click',()=>{switchMarketsTab('explore');$('directory-search').focus()});$('company-reload').addEventListener('click',()=>{E.fundamentals.delete($('company-select').value);loadCompany()});$('company-select').addEventListener('change',()=>{const sym=$('company-select').value;if(safeSymbol(sym)&&sym!==E.selected)setSelected(sym);if(typeof FinancialHealth==='undefined'||document.querySelector('#view-company .fh-legacy')?.open)loadCompany();else $('company-content').textContent='Open this section to load the selected company’s provider profile and ratios.';});$('forecast-select').addEventListener('change',()=>{const sym=$('forecast-select').value;if(safeSymbol(sym)&&sym!==E.selected)setSelected(sym);forecastRunId++;$('forecast-content').innerHTML='<div class="empty-state"><h3>Select Calculate scenarios for '+escapeHtml(sym||'this company')+'</h3><p>Previous forecasts are cleared when changing stocks. The chart and research views use this same ticker.</p></div>'});$('forecast-calculate').addEventListener('click',runForecast);$('chart-show-forecast').addEventListener('change',e=>{E.forecastEnabled=e.target.checked;E.chartForecast=null;if(E.forecastEnabled&&['1H','1D'].includes(E.range)){toast('Forecasts use verified daily closes. Showing the 1Y chart.');setChartRange('1Y')}else loadChart(E.forecastEnabled);});$('news-refresh').addEventListener('click',()=>loadNews(true));$('save-note').addEventListener('click',saveNote);$('export-notes').addEventListener('click',exportNotes);$('save-key').addEventListener('click',saveToken);$('massive-save-key').addEventListener('click',saveMassiveToken);$('massive-clear-key').addEventListener('click',clearMassiveToken);$('massive-test').addEventListener('click',testMassive);$('clear-key').addEventListener('click',clearToken);$('diagnostic-refresh').addEventListener('click',runDiagnostics);$('local-audit-run').addEventListener('click',runLocalAudit);$('export-workspace').addEventListener('click',exportWorkspace);$('import-workspace').addEventListener('change',e=>importWorkspace(e.target.files?.[0]));window.addEventListener('marketdesk:preference-saved',queueWorkspaceBackup);$('symbol-search').addEventListener('input',e=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>searchStocks(e.target.value),360)});document.addEventListener('click',e=>{const tab=e.target.closest('[data-market-tab-link]');if(tab){changeView('markets');switchMarketsTab(tab.dataset.marketTabLink);return}const research=e.target.closest('[data-stock-research]');if(research){openStockResearch(research.dataset.stockResearch);return}const add=e.target.closest('[data-add]');if(add){addStock(add.dataset.add,add.dataset.name);$('search-results').classList.add('hidden');$('symbol-search').value='';return}const rm=e.target.closest('[data-remove]');if(rm){removeStock(rm.dataset.remove);return}const sel=e.target.closest('[data-select]');if(sel){openStock(sel.dataset.select);return}const edit=e.target.closest('[data-editnote]');if(edit){let i=Number(edit.dataset.editnote),n=E.notes[i];if(!n)return;E.editIndex=i;$('note-title').value=n.title;$('note-thesis').value=n.thesis;$('note-risk').value=n.risk;$('note-evidence').value=n.evidence;toast('Editing saved note. Save to update it.');return}const del=e.target.closest('[data-deletenote]');if(del){E.notes.splice(Number(del.dataset.deletenote),1);saveJSON('md-reborn-notes',E.notes);renderNotes();return}let act=e.target.closest('[data-action]');if(act){changeView(act.dataset.action==='all-news'?'news':'markets');return}if(!e.target.closest('.search-panel'))$('search-results').classList.add('hidden')});document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('search-results').classList.add('hidden');if($('main-chart-panel').classList.contains('is-expanded'))toggleExpandedChart(false);if(typeof tapeEscape==='function')tapeEscape()}if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-select]')){e.preventDefault();openStock(e.target.dataset.select)}});document.querySelectorAll('#overview-ranges button').forEach(b=>b.addEventListener('click',()=>setChartRange(b.dataset.range)));let canvas=$('overview-chart'),hoverFrame=0;const queueHover=()=>{if(!hoverFrame)hoverFrame=requestAnimationFrame(()=>{hoverFrame=0;drawChart()})};canvas.addEventListener('mousemove',e=>{E.chartHover=e.clientX-canvas.getBoundingClientRect().left;queueHover()});canvas.addEventListener('mouseleave',()=>{E.chartHover=null;queueHover()});let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(drawChart,80)});window.addEventListener('beforeunload',()=>{if(backupTimer){clearTimeout(backupTimer);sendWorkspaceBackup()}stopWS()})}
async function init(){await restoreWorkspace();const stored=savedJSON('md-reborn-watch',DEFAULT_STOCKS);E.watch=normaliseWatchlist(stored);if(!E.watch.includes(E.selected))E.selected=E.watch[0]||'';Object.assign(E.names,savedJSON('md-reborn-names',{}));E.notes=Array.isArray(savedJSON('md-reborn-notes',[]))?savedJSON('md-reborn-notes',[]):[];const hour=new Date().getHours();$('greeting-time').textContent=hour<12?'morning':hour<17?'afternoon':'evening';setInterval(()=>{$('clock').textContent=new Date().toLocaleTimeString('en-GB',{timeZone:'UTC',hour:'2-digit',minute:'2-digit',second:'2-digit'})+' UTC';syncConnectionUI();refreshWatchFreshness()},1000);attachEvents();renderAll();renderNotes();drawChart();loadChart();E.initialised=true;window.dispatchEvent(new Event('marketdesk:ready'));if(typeof V3!=='undefined')changeView('home');nextQuoteCycleAt=nowMs()+QUOTE_CYCLE_MS;setupTokenStatus();setInterval(()=>{nextQuoteCycleAt=nowMs()+QUOTE_CYCLE_MS;autoQuoteCycle()},QUOTE_CYCLE_MS);setInterval(()=>{renderOverview();renderMarkets();updateTicker()},35000)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();

function setupHistoryImport(){
  const form=$('history-import-form'),status=$('history-import-status');if(!form)return;
  form.addEventListener('submit',async event=>{
    event.preventDefault();const sym=E.selected,button=$('history-import-save'),file=$('history-import-file').files[0];
    if(!file){status.textContent='Choose a CSV file first.';return}if(file.size>900000){status.textContent='Choose a CSV smaller than 900 KB.';return}
    button.disabled=true;status.textContent='Checking your daily prices for '+sym+'…';
    try{
      const result=await post('/api/imported-history',{symbol:sym,csv:await file.text(),source:$('history-import-source').value,confirmed:$('history-import-confirm').checked,split_adjusted:$('history-import-adjustment').value==='adjusted'});
      historyRevision++;pendingHistory.clear();E.candles.clear();status.textContent='Saved '+result.count+' daily prices for '+sym+' on this Mac. Imported data replaces the daily chart for this stock until you choose Use provider history. Intraday charts stay separate.';
      form.reset();if(typeof Desk!=='undefined')Desk.reload();if(E.selected===sym)setChartRange('5Y');
    }catch(error){status.textContent='Could not import: '+error.message}finally{button.disabled=false}
  });
  $('history-import-clear').addEventListener('click',async()=>{
    const sym=E.selected;try{await post('/api/imported-history',{symbol:sym,clear:true});historyRevision++;pendingHistory.clear();E.candles.clear();status.textContent='Imported prices removed for '+sym+'. Using provider history where available.';if(typeof Desk!=='undefined')Desk.reload();if(E.selected===sym)loadChart()}catch(error){status.textContent=error.message}
  });
}

if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('marketdesk:design-saved',queueWorkspaceBackup);
