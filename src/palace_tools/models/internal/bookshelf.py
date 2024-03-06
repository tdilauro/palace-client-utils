from palace_tools.models.api.opds2 import OPDS2Feed


def print_bookshelf_summary(bookshelf: OPDS2Feed) -> None:
    pubs = bookshelf.publications

    print(
        bookshelf.metadata.get("title")
        if hasattr(bookshelf, "metadata")
        else "Bookshelf"
    )
    if not pubs:
        print("  No books on shelf.")
        return

    loans = [pub for pub in pubs if pub.is_loan]
    holds = [pub for pub in pubs if not pub.is_loan]

    print("\n", "  Loans:" if loans else "  No loans.", sep="")
    for p in loans:
        print(f"\n    {p.metadata.title}  ({p.metadata.author.name})")
        for link in p.acquisition_links:
            print(f"      Fulfillment url: {link.href}")
            for indirect in (
                lnk for lnk in link.indirect_acquisition_links if lnk.get("type")
            ):
                print(f"        Indirect type: {indirect['type']}")
            if hashed_pw := link.properties.get("lcp_hashed_passphrase"):
                print(f"      LCP hashed passphrase: {hashed_pw}")
    print("\n", "  Holds:" if holds else "  No holds.", sep="")
    for p in holds:
        print(f"    {p.metadata.title}")
