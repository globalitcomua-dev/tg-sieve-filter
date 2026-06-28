from app.filters.detector import is_filter_request_candidate


def test_accepts_real_request_shapes():
    assert is_filter_request_candidate(
        "NEW - stanislavhapko@gmail.com - imap://post@mail/OFFSHORE/+Clients/CoCo%20Opt"
    )
    assert is_filter_request_candidate(
        "banking@premierplus.com.cy -imap://post@mail/OFFSHORE/+CSPs/Cyprus_Papadakis"
    )
    assert is_filter_request_candidate(
        "Hi! @TeamLead Please new diane.vidot@global-ags.com і все, що завершується на "
        "@global-ags.com to imap://post@mail/OFFSHORE/+CSPs/SEYCHELLES/SEYCH_Mayfair"
    )


def test_rejects_status_and_instruction_messages():
    assert not is_filter_request_candidate(
        "Done NEW - lyashenko.o@gmail.com - imap://post@mail/OFFSHORE/+Clients/Capeman"
    )
    assert not is_filter_request_candidate(
        "Created NEW - @samplebank.example - imap://post@mail.global-it.com.ua/OFFSHORE/+Banks/SAMPLE_BANK"
    )
    assert not is_filter_request_candidate(
        "Добрый день, эта группа создана для более удобного оформления заявок. "
        "Работник, который хочет создать фильтр, пишет в этот чат сообщение стандартной "
        "формы: NEW - @globalnetint.com - imap://post@mail/OFFSHORE/Merchant_Providers/GlobalNetInt"
    )
