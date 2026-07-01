"""Item tracking (QR) domain — public provenance timelines for parts.

A maker generates a tracking *group* for one Contribution plus one tracking
*item* per printed unit; each carries an unguessable ``tracking_token`` that
appears in the public ``/track/{token}`` URL a QR code encodes. Anyone who
can view a token (per its visibility tier) can append a timestamped record.
"""
