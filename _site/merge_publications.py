import re
from difflib import SequenceMatcher
from collections import defaultdict

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def parse_dblp_file(filepath):
    """Parse DBLP file format"""
    publications = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    i = 0
    current_year = None

    while i < len(lines):
        line = lines[i].strip()

        if re.match(r'^\d{4}$', line):
            current_year = int(line)
            i += 1
            continue

        match = re.match(r'\[(j|c|i)(\d+)\]\s+(.+?):\s*$', line)
        if match:
            pub_type, pub_num, authors = match.groups()
            i += 1

            title_lines = []
            while i < len(lines) and not re.match(r'\[(j|c|i)\d+\]', lines[i]) and not re.match(r'^\d{4}$', lines[i].strip()):
                title_line = lines[i].strip()
                if title_line:
                    title_lines.append(title_line)
                    i += 1
                    break
                else:
                    i += 1

            if title_lines:
                title_venue = ' '.join(title_lines)
                year_match = re.search(r'\((\d{4})\)\s*$', title_venue)
                year = int(year_match.group(1)) if year_match else current_year

                parts = title_venue.split('. ', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    venue = parts[1].strip()
                else:
                    title = title_venue
                    venue = ''

                publications.append({
                    'type': pub_type,
                    'number': int(pub_num),
                    'authors': authors.strip(),
                    'title': title,
                    'venue': venue,
                    'year': year,
                    'source': 'dblp'
                })
        else:
            i += 1

    return publications

def parse_google_scholar_file(filepath):
    """Parse Google Scholar export - title is first, then authors/venue"""
    publications = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line or line in ['TITLE', 'CITED BY', 'YEAR', 'PrivacyTermsHelp'] or 'Articles' in line:
            i += 1
            continue

        # Line is the title
        title = line
        i += 1

        if i >= len(lines):
            break

        # Next line: authors + venue, citations, year (tab separated)
        info_line = lines[i].strip()
        parts = info_line.split('\t')

        if len(parts) >= 2:
            authors_venue = parts[0]
            year_str = parts[-1]

            try:
                year = int(year_str)
            except:
                year = None

            # Separate authors from venue
            venue = ''
            authors = authors_venue

            # Venue keywords
            venue_match = re.search(r'((?:arXiv preprint|IEEE|Proceedings of|Advances in|Forty|ACM|International Conference|Transactions|CRC Press|Applied AI|The |Annual Conference)[^,\t]+)', authors_venue)
            if venue_match:
                venue = venue_match.group(1).strip()
                authors = authors_venue[:venue_match.start()].strip().rstrip(',')

            publications.append({
                'title': title,
                'authors': authors,
                'venue': venue,
                'year': year,
                'source': 'google_scholar'
            })

        i += 1

    return publications

def extract_conference_name(venue_text):
    """Extract conference/journal abbreviation from venue string"""
    venue_lower = venue_text.lower()

    # Conference mappings
    conf_map = {
        'neurips': 'NeurIPS',
        'icml': 'ICML',
        'iclr': 'ICLR',
        'aaai': 'AAAI',
        'ijcai': 'IJCAI',
        'kdd': 'KDD',
        'www': 'WWW',
        'sigir': 'SIGIR',
        'acl': 'ACL',
        'emnlp': 'EMNLP',
        'cvpr': 'CVPR',
        'iccv': 'ICCV',
        'eccv': 'ECCV',
        'cikm': 'CIKM',
        'vldb': 'VLDB',
        'sigmod': 'SIGMOD',
        'icde': 'ICDE',
        'mm': 'MM',
        'adma': 'ADMA',
        'icassp': 'ICASSP',
        'sdm': 'SDM',
        'sigspatial': 'SIGSPATIAL'
    }

    for key, name in conf_map.items():
        if key in venue_lower:
            return name

    # Check for journal patterns
    if 'ieee' in venue_lower:
        if 'artif. intell' in venue_lower or 'artificial intelligence' in venue_lower:
            return 'IEEE TAI'
        elif 'knowl. data eng' in venue_lower or 'knowledge and data' in venue_lower:
            return 'IEEE TKDE'
        elif 'neural networks' in venue_lower:
            return 'IEEE TNNLS'
        elif 'autom. sci. eng' in venue_lower or 'automation science' in venue_lower:
            return 'IEEE TASE'
        elif 'inf. forensics' in venue_lower:
            return 'IEEE TIFS'

    if 'acm trans' in venue_lower and 'inf. syst' in venue_lower:
        return 'ACM TOIS'

    return None

def format_venue_with_year(venue, year):
    """Format venue with highlighting"""
    conf_name = extract_conference_name(venue)
    year_suffix = f"'{str(year)[-2:]}" if year else ''

    if conf_name:
        # Top-tier ML conferences in red
        if conf_name in ['NeurIPS', 'ICML', 'ICLR']:
            return f'<strong style="color: red;">{conf_name}{year_suffix}</strong>'
        # Other major venues in blue
        else:
            return f'<strong style="color: #4a86e8;">{conf_name}{year_suffix}</strong>'

    # Return original venue if no match
    return venue

def main():
    # Parse both files
    dblp_pubs = parse_dblp_file('/Users/wanghao112/Downloads/howardzju.github.io/main/dblp')
    gs_pubs = parse_google_scholar_file('/Users/wanghao112/Downloads/howardzju.github.io/main/google_scholar')

    print(f"Parsed {len(dblp_pubs)} publications from DBLP")
    print(f"Parsed {len(gs_pubs)} publications from Google Scholar")

    # Match publications by title similarity
    matched = []
    used_gs = set()

    for dblp_pub in dblp_pubs:
        if not dblp_pub['year'] or dblp_pub['year'] < 2022:
            continue

        best_match = None
        best_score = 0
        best_idx = -1

        for gs_idx, gs_pub in enumerate(gs_pubs):
            if gs_idx in used_gs:
                continue

            title_sim = similarity(dblp_pub['title'], gs_pub['title'])
            year_match = 1.0 if (dblp_pub['year'] == gs_pub['year']) else 0.0
            score = title_sim * 0.9 + year_match * 0.1

            if score > best_score and title_sim > 0.6:
                best_score = score
                best_match = gs_pub
                best_idx = gs_idx

        if best_match and best_score > 0.65:
            # Use DBLP authors (more complete), GS title and venue (more accurate)
            merged = {
                'authors': dblp_pub['authors'],
                'title': best_match['title'],
                'venue': best_match['venue'] if best_match['venue'] else dblp_pub['venue'],
                'year': dblp_pub['year'],
                'type': dblp_pub['type'],
                'number': dblp_pub['number']
            }
            matched.append(merged)
            used_gs.add(best_idx)
        else:
            # Use DBLP data only
            matched.append(dblp_pub)

    # Add unmatched Google Scholar pubs (2022-2026)
    for idx, gs_pub in enumerate(gs_pubs):
        if idx not in used_gs and gs_pub['year'] and gs_pub['year'] >= 2022:
            matched.append(gs_pub)

    # Sort by year descending
    matched.sort(key=lambda x: (-x['year'] if x['year'] else 0, x.get('type', 'z'), -x.get('number', 0)))

    # Group by year
    by_year = defaultdict(list)
    for pub in matched:
        by_year[pub['year']].append(pub)

    # Generate HTML
    html_lines = []
    html_lines.append('<div class="mt-3" style="font-size: 15px;">')

    for year in sorted(by_year.keys(), reverse=True):
        html_lines.append(f'    <h4 class="pt-3">{year}</h4>')
        html_lines.append('    <ul>')

        for pub in by_year[year]:
            # Format authors - bold Hao Wang, handle * for corresponding author
            authors = pub['authors']
            authors = re.sub(r'\bHao Wang#', '<strong>Hao Wang*</strong>', authors)
            authors = re.sub(r'\bHao Wang\b', '<strong>Hao Wang</strong>', authors)

            title = pub['title']
            venue_html = format_venue_with_year(pub['venue'], pub['year'])

            html_lines.append(f'        <li class="mb-2">{authors}, "{title}," {venue_html}.</li>')

        html_lines.append('    </ul>')

    html_lines.append('</div>')

    # Write output
    output_path = '/Users/wanghao112/Downloads/howardzju.github.io/main/pages/publications_new.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))

    print(f"\nGenerated {len(matched)} publications (2022-2026)")
    for year in sorted(by_year.keys(), reverse=True):
        print(f"  {year}: {len(by_year[year])} publications")
    print(f"\nSaved to: {output_path}")

if __name__ == '__main__':
    main()
