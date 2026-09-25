// SPDX-License-Identifier: MPL-2.0
/**
 * @file
 * @copyright
 * This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
 * If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 * @author Thomas Vogt, thomas@thomas-vogt.de
 *
 * @brief Declaration of Class Tftp::Packets::PacketStatistic.
 **/

#ifndef TFTP_PACKETS_PACKETSTATISTIC_HPP
#define TFTP_PACKETS_PACKETSTATISTIC_HPP

#include <tftp/packets/Packets.hpp>

#include <iosfwd>
#include <map>
#include <mutex>
#include <string>
#include <tuple>

namespace Tftp::Packets {

/**
 * @brief TFTP Packet Statistic.
 *
 * This class provides operations to count packets (count and total size).
 * The statistic is separated into packet type.
 *
 * The class provides to global instances for transmit and receive distinction.
 * The @ref PacketHandler used @ref globalReceive for logging received packets.
 * The @ref Clients::Operation, @ref Servers::Server, and @ref Servers::Operation used the @ref globalTransmit() for
 * logging transmitted packets.
 *
 * There is no distinction between multiple clients, operations, nor client/server.
 **/
class TFTP_EXPORT PacketStatistic
{
  public:
    //! Statistic Value Type (Count, Size)
    using Value = std::tuple< std::size_t, std::size_t >;
    //! Statistic Type
    using Statistic = std::map< PacketType, Value >;

    /**
     * @brief Global Receive Packet Statistic counter.
     *
     * @return Global Receive Packet Statistic counter.
     **/
    [[nodiscard]] static PacketStatistic& globalReceive();

    /**
     * @brief Global Transmit Packet Statistic counter.
     *
     * @return Global Transmit Packet Statistic counter.
     **/
    [[nodiscard]] static PacketStatistic& globalTransmit();

    /**
     * @brief Accumulates all Statistic values to one overall result.
     *
     * @param[in] statistic
     *   Packet Statistic information
     *
     * @return Total information.
     **/
    [[nodiscard]] static Value total( const Statistic &statistic );

    //! Default Constructor
    PacketStatistic() = default;

    /**
     * @brief Log a sent packet.
     *
     * @param[in] type
     *   Packet Type
     * @param[in] size
     *   Packet Size
     **/
    void packet( PacketType type, size_t size );

    /**
     * @brief Returns the "sent" statistic.
     *
     * @return Sent Packet statistic.
     **/
    [[nodiscard]] Statistic statistic() const;

    /**
     * @brief Reset the statistic counters.
     **/
    void reset();

    /**
     * @brief Gives the statistic as printable string.
     *
     * @return Static as string representation
     **/
    [[nodiscard]] std::string toString() const;

  private:
    //! Sent statistic
    Statistic statisticV;
    //! Mutex protecting the access to @p statisticV
    mutable std::mutex mutex;
};

/**
 * @brief Stream output operator of @p PacketStatistic.
 *
 * @param[in,out] stream
 *   Output Stream
 * @param[in] statistic
 *   Packet Statistic
 *
 * @return @p stream for chaining.
 **/
TFTP_EXPORT std::ostream& operator<<( std::ostream &stream, const PacketStatistic &statistic );

}

#endif
