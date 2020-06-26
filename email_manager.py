import shared

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl
import xml.dom.minidom
import xml.etree.ElementTree as ET


def current_time():
    return datetime.now().strftime("%b %d %Y @ %I:%M %p")


def format_html_listing(el, listing, optional=None):
    link_el = ET.SubElement(el, 'a', {'href': shared.PARAMS['str'][listing.source] + str(listing.mls_id)})
    link_el.text = shared.PARAMS['str'][listing.source] + str(listing.mls_id)
    list_el = ET.SubElement(el, 'ul')
    if optional:
        optional_el = ET.SubElement(list_el, 'li')
        strong_el = ET.SubElement(optional_el, 'strong')
        strong_el.text = optional
    status_el = ET.SubElement(list_el, 'li')
    status_el.text = 'Status: {}'.format(listing.status)
    price_el = ET.SubElement(list_el, 'li')
    if listing.open_house:
        open_house_el = ET.SubElement(list_el, 'li')
        open_house_el.text = listing.open_house
    price_el.text = 'Price: ${:,}'.format(listing.price)
    address_el = ET.SubElement(list_el, 'li')
    address_el.text = 'Address: {}'.format(listing.address)
    details_el = ET.SubElement(list_el, 'li')
    details_el.text = '{} SqFt • {} Bds • {} Ba '.format(listing.sqft, listing.bedrooms, listing.bathrooms)
    details_el = ET.SubElement(list_el, 'li')
    details_el.text = 'Agent: {}'.format(listing.agent)
    return el


def format_html_search_parameters(el):
    ET.SubElement(el, 'hr')
    ET.SubElement(el, 'h3').text = 'Search parameters'
    search_params_ul_el = ET.SubElement(el, 'ul')
    ure_li_el = ET.SubElement(search_params_ul_el, 'li')
    ure_subtitle_el = ET.SubElement(ure_li_el, 'h4')
    ure_subtitle_el.text = 'Utah Real Estate - '
    ure_a_el = ET.SubElement(ure_subtitle_el, 'a', {'href': shared.PARAMS['scrape']['ure']})
    ure_a_el.text = 'Link'
    ure_details_ul_el = ET.SubElement(ure_li_el, 'ul')
    ET.SubElement(ure_details_ul_el, 'li').text = f'Location query: {shared.CONFIG["search"]["geolocation"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Min Price: {shared.CONFIG["search"]["min_price"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Max Price: {shared.CONFIG["search"]["max_price"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Bedrooms: {shared.CONFIG["search"]["bedrooms_dropdown"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Bathrooms: {shared.CONFIG["search"]["bathrooms_dropdown"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Square Feet: {shared.CONFIG["search"]["square_feet_dropdown"]}'
    ET.SubElement(ure_details_ul_el, 'li').text = f'Acres: {shared.CONFIG["search"]["acres_dropdown"]}'
    ksl_li_el = ET.SubElement(search_params_ul_el, 'li')
    ksl_subtitle_el = ET.SubElement(ksl_li_el, 'h4')
    ksl_subtitle_el.text = 'KSL Classifieds - '
    ET.SubElement(ksl_subtitle_el, 'a', {'href': shared.CONFIG['search']['ksl']}).text = 'Link'
    return el


def generate_email_msg(listings, new_listing_ids, more_available_ids, price_drop_ids, open_house_ids):
    message = MIMEMultipart("alternative")
    title = 'Utah Real Estate Update {}'.format(current_time())
    message["Subject"] = title
    html_el = ET.Element('html')
    body_el = ET.SubElement(html_el, 'body')
    text = ''
    if new_listing_ids:
        text += 'New in Cache County, Utah:\n'
        title_el = ET.SubElement(body_el, 'h2')
        title_el.text = 'New in Cache County, Utah'
        list_el = ET.SubElement(body_el, 'ul')
        for new_mls_num in new_listing_ids:
            text += '\n - ' + shared.PARAMS['str'][listings[new_mls_num].source] + str(new_mls_num)
            li = ET.SubElement(list_el, 'li')
            format_html_listing(li, listings[new_mls_num])
    if more_available_ids:
        text += 'Available again in Cache County, Utah:\n'
        title_el = ET.SubElement(body_el, 'h2')
        title_el.text = 'Available again in Cache County, Utah'
        list_el = ET.SubElement(body_el, 'ul')
        for more_availabe_id in more_available_ids.keys():
            text += '\n - ' + shared.PARAMS['str'][listings[more_availabe_id].source] + str(more_availabe_id)
            text += '\n\t - ' + more_available_ids[more_availabe_id]
            li = ET.SubElement(list_el, 'li')
            format_html_listing(li, listings[more_availabe_id], more_available_ids[more_availabe_id])
    if price_drop_ids:
        text += 'Price drop in Cache County, Utah:\n'
        title_el = ET.SubElement(body_el, 'h2')
        title_el.text = 'Price drop in Cache County, Utah'
        list_el = ET.SubElement(body_el, 'ul')
        for price_drop_id in price_drop_ids.keys():
            text += '\n - ' + shared.PARAMS['str'][listings[price_drop_id].source] + str(price_drop_id)
            text += '\n\t - ' + price_drop_ids[price_drop_id]
            li = ET.SubElement(list_el, 'li')
            format_html_listing(li, listings[price_drop_id], price_drop_ids[price_drop_id])
    if open_house_ids:
        text += 'Open house in Cache County, Utah:\n'
        title_el = ET.SubElement(body_el, 'h2')
        title_el.text = 'Open house in Cache County, Utah'
        list_el = ET.SubElement(body_el, 'ul')
        for open_house_id in open_house_ids.keys():
            text += '\n - ' + shared.PARAMS['str'][listings[open_house_id].source] + str(open_house_id)
            text += '\n\t - ' + open_house_ids[open_house_id]
            li = ET.SubElement(list_el, 'li')
            format_html_listing(li, listings[open_house_id], open_house_ids[open_house_id])
    format_html_search_parameters(body_el)
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(xml.dom.minidom.parseString(ET.tostring(html_el)).toprettyxml(), "html"))
    return message


def send_email(message):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    message['From'] = shared.CONFIG['email']['from']
    recipients = shared.CONFIG['email']['to'].split(' ')
    message["To"] = ', '.join(recipients)
    if shared.SEND_MESSAGE:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(shared.CONFIG['email']['from'], shared.CONFIG['email']['password'])
            server.sendmail(message['From'], recipients, message.as_string())
        shared.log_message('Email sent')
    else:
        log = '***** DUMMY EMAIL *****\n'
        log += '********* TO: *********\n'
        log += message['To'] + '\n'
        log += '******** FROM: ********\n'
        log += message['From'] + '\n'
        log += '****** MESSAGE: *******\n'
        log += message.as_string() + '\n'
        log += '***********************'
        shared.log_message(log)


def generate_and_send_email(listings, new_listing_ids, more_available_ids, price_drop_ids, open_house_ids):
    send_email(generate_email_msg(listings, new_listing_ids, more_available_ids, price_drop_ids, open_house_ids))


def test():
    message = MIMEMultipart("alternative")
    message["Subject"] = 'Test Email'
    message.attach(MIMEText('This is a test email for the Utah Real Estate alerts program', "plain"))
    p_el = ET.Element('p')
    p_el.text = 'This is a test email for the Utah Real Estate alerts program'
    message.attach(MIMEText(xml.dom.minidom.parseString(ET.tostring(p_el)).toprettyxml(), "html"))
    send_email(message)


if __name__ == '__main__':
    test()
